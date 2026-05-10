from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_schema_patches() -> None:
    """Apply additive changes when the DB predates new columns (create_all does not alter SQLite)."""
    try:
        insp = inspect(engine)
        names = insp.get_table_names()
    except Exception:
        return
    if "site_settings" in names:
        col_names = {c["name"] for c in insp.get_columns("site_settings")}
        if "logo_url" not in col_names:
            stmt = text(
                "ALTER TABLE site_settings ADD COLUMN logo_url VARCHAR(500) NOT NULL DEFAULT ''"
            )
            with engine.begin() as conn:
                conn.execute(stmt)
        col_names = {c["name"] for c in insp.get_columns("site_settings")}
        if "map_lat" not in col_names:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE site_settings ADD COLUMN map_lat VARCHAR(32) NOT NULL DEFAULT ''")
                )
        col_names = {c["name"] for c in insp.get_columns("site_settings")}
        if "map_lng" not in col_names:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE site_settings ADD COLUMN map_lng VARCHAR(32) NOT NULL DEFAULT ''")
                )

    if "services" in names:
        svc_cols = {c["name"] for c in insp.get_columns("services")}
        # Legacy DBs: add FK column when services predates service_categories link
        if "category_id" not in svc_cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE services ADD COLUMN category_id INTEGER REFERENCES service_categories(id)"
                    )
                )
        if "source_item_id" not in svc_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE services ADD COLUMN source_item_id VARCHAR(64)"))

    if "service_categories" in names:
        sc_cols = {c["name"] for c in insp.get_columns("service_categories")}
        if "reference_url" not in sc_cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE service_categories ADD COLUMN reference_url VARCHAR(500) NOT NULL DEFAULT ''"
                    )
                )

    # Visit line items: catalog services (replaces menu_items).
    if "customer_service_visit_services" not in names:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE customer_service_visit_services (
                        visit_id INTEGER NOT NULL REFERENCES customer_service_visits(id) ON DELETE CASCADE,
                        service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
                        PRIMARY KEY (visit_id, service_id)
                    )
                    """
                )
            )

    if "customer_service_visit_menu_items" in names:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS customer_service_visit_menu_items"))

    if "menu_items" in names:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS menu_items"))

    # Service history → stylists FK (replaces free-text stylist_name on legacy DBs).
    if "api_settings" in names:
        api_cols = {c["name"] for c in insp.get_columns("api_settings")}
        if "whatsapp_webhook_verify_token" not in api_cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE api_settings ADD COLUMN whatsapp_webhook_verify_token "
                        "VARCHAR(255) NOT NULL DEFAULT ''"
                    )
                )
        if "whatsapp_app_secret" not in api_cols:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE api_settings ADD COLUMN whatsapp_app_secret TEXT NOT NULL DEFAULT ''"
                    )
                )

    if "customer_service_visits" in names:
        vcols = {c["name"] for c in insp.get_columns("customer_service_visits")}
        if "stylist_id" not in vcols and "stylists" in insp.get_table_names():
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE customer_service_visits ADD COLUMN stylist_id INTEGER "
                        "REFERENCES stylists(id)"
                    )
                )
        vcols = {c["name"] for c in inspect(engine).get_columns("customer_service_visits")}
        if "stylist_name" in vcols and "stylist_id" in vcols:
            _migrate_stylist_name_to_fk()


class Base(DeclarativeBase):
    pass


def _migrate_stylist_name_to_fk() -> None:
    """Create Stylist rows from legacy stylist_name text, link visits, drop old column (SQLite 3.35+)."""
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT DISTINCT TRIM(stylist_name) AS n FROM customer_service_visits "
                    "WHERE stylist_name IS NOT NULL AND TRIM(stylist_name) != ''"
                )
            ).fetchall()
            for (name,) in rows:
                if not name:
                    continue
                exists = conn.execute(
                    text("SELECT 1 FROM stylists WHERE full_name = :n LIMIT 1"), {"n": name}
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    text(
                        "INSERT INTO stylists (full_name, phone, notes, sort_order, is_active) "
                        "VALUES (:n, '', '', 0, 1)"
                    ),
                    {"n": name},
                )
            conn.execute(
                text(
                    """
                    UPDATE customer_service_visits SET stylist_id = (
                        SELECT s.id FROM stylists s
                        WHERE s.full_name = TRIM(customer_service_visits.stylist_name)
                    )
                    WHERE stylist_name IS NOT NULL AND TRIM(stylist_name) != ''
                      AND stylist_id IS NULL
                    """
                )
            )
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE customer_service_visits DROP COLUMN stylist_name"))
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
