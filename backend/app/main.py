import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from app.admin_setup import mount_admin
from app.config import get_settings
from app.database import Base, SessionLocal, engine, run_schema_patches
from app.routers import api_router
from app.webhooks_whatsapp import router as whatsapp_webhook_router
from app.essence_sync import sync_essence_hair_skin_services
from app.seed import (
    ensure_body_category_and_services,
    ensure_make_up_category_and_services,
    ensure_mani_pedi_category_and_services,
    ensure_nails_category_and_services,
    ensure_pre_bridal_category_and_services,
    migrate_legacy_service_categories,
    seed_if_empty,
)
from app.site_media import ensure_placeholder_asset
from app.upload_storage import ensure_upload_root


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_schema_patches()
    s = get_settings()
    ensure_upload_root(Path(s.upload_dir))
    db = SessionLocal()
    try:
        migrate_legacy_service_categories(db)
        seed_if_empty(db)
        sync_essence_hair_skin_services(db)
        ensure_nails_category_and_services(db)
        ensure_body_category_and_services(db)
        ensure_mani_pedi_category_and_services(db)
        ensure_make_up_category_and_services(db)
        ensure_pre_bridal_category_and_services(db)
    finally:
        db.close()
    yield


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SAL_ROOT = _BACKEND_ROOT.parent
# Optional bundled theme copy at backend/saul-dist; else use repo saul_html_free tree.
_SAUL_DIST = _BACKEND_ROOT / "saul-dist"
if not _SAUL_DIST.is_dir():
    _SAUL_DIST = _SAL_ROOT / "saul_html_free_v1.0.0" / "theme" / "dist"
_settings = get_settings()
_upload_path = Path(_settings.upload_dir)
ensure_upload_root(_upload_path)
_spa_dir_env = (_settings.spa_dist or "").strip()
_FRONTEND_DIST = (
    Path(_spa_dir_env).expanduser().resolve()
    if _spa_dir_env
    else (_SAL_ROOT / "frontend" / "dist").resolve()
)

_site_media_dir = _BACKEND_ROOT / "site_media"
_site_media_dir.mkdir(parents=True, exist_ok=True)
ensure_placeholder_asset(_site_media_dir)

app = FastAPI(title="Adore Professional Salon API", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory=str(_upload_path)), name="uploads")
app.mount(
    "/site-media",
    StaticFiles(directory=str(_site_media_dir)),
    name="site_media",
)
app.mount(
    "/admin-theme",
    StaticFiles(directory=str(_BACKEND_ROOT / "admin_static")),
    name="admin_theme",
)
if _SAUL_DIST.is_dir():
    app.mount(
        "/saul-admin",
        StaticFiles(directory=str(_SAUL_DIST)),
        name="saul_admin",
    )

_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or _default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(whatsapp_webhook_router, prefix="/webhooks")
mount_admin(app)


@app.get("/admin", include_in_schema=False)
async def admin_redirect_no_trailing_slash() -> RedirectResponse:
    """SQLAdmin is mounted at ``/admin/``; bare ``/admin`` otherwise falls through to the SPA catch-all."""
    return RedirectResponse(url="/admin/", status_code=307)


_log = logging.getLogger("sal.errors")


def _install_public_spa(application: FastAPI, dist: Path) -> bool:
    """Serve the Vite production build from ``dist`` (same origin as API). Register last."""
    index = dist / "index.html"
    if not dist.is_dir() or not index.is_file():
        return False

    dist_root = dist.resolve()

    @application.get("/", include_in_schema=False)
    async def spa_home():
        return FileResponse(index)

    @application.get("/{full_path:path}", include_in_schema=False)
    async def spa_history_fallback(full_path: str):
        if ".." in full_path.split("/"):
            raise HTTPException(status_code=404)
        target = (dist / full_path).resolve()
        try:
            target.relative_to(dist_root)
        except ValueError:
            raise HTTPException(status_code=404)
        if target.is_file():
            return FileResponse(target)
        return FileResponse(index)

    _log.info("Public site: serving SPA from %s", dist_root)
    return True


@app.middleware("http")
async def log_unhandled_exceptions(request: Request, call_next):
    """Log full tracebacks to the uvicorn terminal when any route raises."""
    try:
        return await call_next(request)
    except Exception:
        _log.error(
            "%s %s\n%s",
            request.method,
            request.url.path,
            traceback.format_exc(),
        )
        raise


@app.get("/health")
def health() -> dict[str, str]:
    from app.admin_forms import SAL_SITE_SETTINGS_FORM_REV

    return {"status": "ok", "sal_site_settings_form_rev": SAL_SITE_SETTINGS_FORM_REV}


if not _install_public_spa(app, _FRONTEND_DIST):

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "name": "Adore Professional Salon API",
            "docs": "/docs",
            "health": "/health",
            "admin": "/admin",
            "api": "/api",
            "whatsapp_webhook": "/webhooks/whatsapp",
            "hint": "Run `npm run build` in frontend/ to serve the public site here.",
        }
