import re
from datetime import date, datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (
    ApiSettings,
    BlogPost,
    Customer,
    CustomerServiceVisit,
    GalleryImage,
    HeroSlide,
    SalonProduct,
    Service,
    ServiceCategory,
    SiteSettings,
    Stylist,
    Testimonial,
)
from app.brand_defaults import (
    DEFAULT_ADDRESS,
    DEFAULT_EMAIL,
    DEFAULT_HOURS_LINE,
    DEFAULT_MAP_LAT,
    DEFAULT_MAP_LNG,
    DEFAULT_PHONE,
    DEFAULT_SALON_NAME,
    _LEGACY_SALON_NAMES,
    _LEGACY_US_FAKE_PHONE,
    is_legacy_placeholder_address,
)
from app.site_media import migrate_remote_images_to_site_media, site_media_url


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s[:180] or "item"


def _unique_category_slug(db: Session, base: str) -> str:
    s = base or "item"
    n = 0
    while True:
        cand = s if n == 0 else f"{s}-{n}"
        if db.query(ServiceCategory).filter(ServiceCategory.slug == cand).first() is None:
            return cand
        n += 1


# Categories synced from Essence (Hair + Skin first; more URLs can be added later).
_ESSENCE_CATALOG_ROWS = [
    {
        "name": "Hair",
        "slug": "hair",
        "desc": "Cuts, styling, color & treatments for every hair type.",
        "image": site_media_url("hair.jpg"),
        "sort": 0,
        "reference_url": "https://essence-salon.respark.in/essence-salon-193/portblair/hair-srp",
    },
    {
        "name": "Skin",
        "slug": "skin",
        "desc": "Facials, cleanup, and glow treatments.",
        "image": site_media_url("skin.jpg"),
        "sort": 1,
        "reference_url": "https://essence-salon.respark.in/essence-salon-193/portblair/skin-srp",
    },
]


def migrate_legacy_service_categories(db: Session) -> None:
    """Link services.service_categories: seed categories, backfill from legacy `category` text, drop column."""
    insp = inspect(engine)
    if "service_categories" not in insp.get_table_names():
        return
    svc_cols = {c["name"] for c in insp.get_columns("services")}
    if "category_id" not in svc_cols:
        return

    def _ensure_general(sess: Session) -> ServiceCategory:
        g = sess.query(ServiceCategory).filter(ServiceCategory.slug == "general").first()
        if g is None:
            g = ServiceCategory(
                name="General",
                slug="general",
                image_url="",
                description="",
                sort_order=999,
                is_active=True,
            )
            sess.add(g)
            sess.commit()
            sess.refresh(g)
        return g

    if db.query(ServiceCategory).count() == 0:
        for row in _ESSENCE_CATALOG_ROWS:
            db.add(
                ServiceCategory(
                    name=row["name"],
                    slug=row["slug"],
                    image_url=row["image"],
                    description=row["desc"],
                    sort_order=row["sort"],
                    is_active=True,
                    reference_url=row.get("reference_url", ""),
                )
            )
        db.commit()

    name_to_id = {c.name: c.id for c in db.query(ServiceCategory).all()}

    if "category" in svc_cols:
        result = db.execute(
            text("SELECT id, category FROM services WHERE category_id IS NULL")
        )
        for sid, cat_raw in result.all():
            cat_name = (cat_raw or "").strip() or "General"
            cid = name_to_id.get(cat_name)
            if cid is None:
                sc = ServiceCategory(
                    name=cat_name,
                    slug=_unique_category_slug(db, slugify(cat_name)),
                    image_url="",
                    description="",
                    sort_order=500,
                    is_active=True,
                )
                db.add(sc)
                db.flush()
                cid = sc.id
                name_to_id[cat_name] = cid
            db.execute(
                text("UPDATE services SET category_id = :cid WHERE id = :sid"),
                {"cid": cid, "sid": sid},
            )
        db.commit()

    null_ct = db.execute(text("SELECT COUNT(*) FROM services WHERE category_id IS NULL")).scalar()
    if null_ct:
        gen = _ensure_general(db)
        db.execute(
            text("UPDATE services SET category_id = :cid WHERE category_id IS NULL"),
            {"cid": gen.id},
        )
        db.commit()

    if "category" in svc_cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE services DROP COLUMN category"))
        except Exception:
            pass


def ensure_essence_main_catalog(db: Session) -> None:
    """Ensure Hair/Skin categories exist and reference URLs are set (line items come from Essence sync)."""
    by_slug = {c.slug: c for c in db.query(ServiceCategory).all()}
    for row in _ESSENCE_CATALOG_ROWS:
        ref = row.get("reference_url", "")
        cat = by_slug.get(row["slug"])
        if cat is None:
            cat = ServiceCategory(
                name=row["name"],
                slug=row["slug"],
                image_url=row["image"],
                description=row["desc"],
                sort_order=row["sort"],
                is_active=True,
                reference_url=ref,
            )
            db.add(cat)
            by_slug[row["slug"]] = cat
        else:
            if ref and (not cat.reference_url or cat.reference_url != ref):
                cat.reference_url = ref
            if row["slug"] == "skin":
                cur = (cat.image_url or "").strip()
                if not cur:
                    cat.image_url = row["image"]
    db.commit()


_NAILS_CATEGORY_ROW = {
    "name": "Nails",
    "slug": "nails",
    "desc": "Manicures, nail art, gel, acrylic & spa treatments.",
    "image": site_media_url("nails.jpg"),
    "sort": 2,
}

# Local price list (INR). source_item_id = nails-manual-<slug> so rows survive Essence-style prunes.
_NAILS_PRICE_LIST: list[tuple[str, int]] = [
    ("Change Polish", 100),
    ("Cut File & Polish", 200),
    ("Upgrade To Nails Art", 300),
    ("Upgrade To Gel Polish", 700),
    ("Creative Nail Art Free Hand", 350),
    ("Creative", 660),
    ("Advance", 800),
    ("Application Of Fake Nail Per Tip", 50),
    ("Free Hand Art Per Tip", 50),
    ("Basic Nail Art", 300),
    ("Gel Polish Full Set", 1500),
    ("Gel Polish Removal", 500),
    ("Acrylic Nail Extension Full Set", 3000),
    ("Acrylic Nail Refill", 2000),
    ("Nail Extension Removal", 800),
    ("French Nail Art", 400),
    ("3D Nail Art", 800),
    ("Glitter Nail Art", 500),
    ("Ombre Nails", 700),
    ("Chrome Nails", 900),
    ("Builder Gel Overlay", 1800),
    ("Nail Strengthening Treatment", 1200),
    ("Nail Repair Per Nail", 150),
    ("Cuticle Care Treatment", 300),
    ("Spa Manicure with Nail Art", 1200),
    ("Spa Pedicure with Nail Art", 1500),
]


def ensure_nails_category_and_services(db: Session) -> int:
    """Create Nails category if missing and upsert the static INR price list."""
    meta = _NAILS_CATEGORY_ROW
    cat = db.query(ServiceCategory).filter(ServiceCategory.slug == meta["slug"]).first()
    if cat is None:
        cat = ServiceCategory(
            name=meta["name"],
            slug=meta["slug"],
            image_url=meta["image"],
            description=meta["desc"],
            sort_order=meta["sort"],
            is_active=True,
            reference_url="",
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

    touched = 0
    for order, (title, inr) in enumerate(_NAILS_PRICE_LIST):
        source_key = f"nails-manual-{slugify(title)}"[:64]
        price = f"₹{inr}"
        ex = db.query(Service).filter(Service.source_item_id == source_key).first()
        candidate = f"nails-{slugify(title)}"[:180]
        if candidate == "nails-":
            candidate = f"nails-item-{order}"
        other = db.query(Service).filter(Service.slug == candidate).first()
        if other is not None and (ex is None or other.id != ex.id):
            candidate = f"nails-{order}-{slugify(title)}"[:180]

        if ex:
            ex.category_id = cat.id
            ex.title = title[:200]
            ex.slug = candidate
            ex.short_description = ""
            ex.price_from = price[:64]
            ex.sort_order = order
            ex.is_active = True
        else:
            db.add(
                Service(
                    category_id=cat.id,
                    title=title[:200],
                    slug=candidate,
                    short_description="",
                    image_url="",
                    price_from=price[:64],
                    sort_order=order,
                    is_active=True,
                    source_item_id=source_key,
                )
            )
        touched += 1

    db.commit()
    return touched


_BODY_CATEGORY_ROW = {
    "name": "Body",
    "slug": "body",
    "desc": "Waxing, threading, polishing, massage & body treatments.",
    "image": site_media_url("body.jpg"),
    "sort": 3,
}

_BODY_PRICE_LIST: list[tuple[str, int]] = [
    ("Full Arms Wax", 500),
    ("Half Arms Wax", 300),
    ("Full Legs Wax", 700),
    ("Half Legs Wax", 400),
    ("Underarms Wax", 200),
    ("Full Body Wax", 2500),
    ("Back Wax", 600),
    ("Chest Wax", 600),
    ("Face Wax", 300),
    ("Bikini Wax", 1200),
    ("Brazilian Wax", 1800),
    ("Threading Full Face", 300),
    ("Eyebrow Threading", 50),
    ("Upper Lip Threading", 40),
    ("Chin Threading", 40),
    ("Full Body Polishing", 3000),
    ("Back Polishing", 1500),
    ("Body Scrub", 2000),
    ("Full Body Bleach", 1800),
    ("Face & Body Bleach", 2200),
    ("Back Cleanup", 1200),
    ("Full Body Massage (60 min)", 2500),
    ("Back Massage (30 min)", 1200),
    ("Head + Shoulder Massage", 800),
    ("Aroma Therapy Massage", 3000),
    ("Deep Tissue Massage", 3500),
    ("Relaxation Massage", 2500),
    ("Hot Oil Body Massage", 2800),
    ("Detan Body Treatment", 2000),
]


def ensure_body_category_and_services(db: Session) -> int:
    """Create Body category if missing and upsert the static INR price list."""
    meta = _BODY_CATEGORY_ROW
    cat = db.query(ServiceCategory).filter(ServiceCategory.slug == meta["slug"]).first()
    if cat is None:
        cat = ServiceCategory(
            name=meta["name"],
            slug=meta["slug"],
            image_url=meta["image"],
            description=meta["desc"],
            sort_order=meta["sort"],
            is_active=True,
            reference_url="",
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

    touched = 0
    for order, (title, inr) in enumerate(_BODY_PRICE_LIST):
        source_key = f"body-manual-{slugify(title)}"[:64]
        price = f"₹{inr}"
        ex = db.query(Service).filter(Service.source_item_id == source_key).first()
        candidate = f"body-{slugify(title)}"[:180]
        if candidate == "body-":
            candidate = f"body-item-{order}"
        other = db.query(Service).filter(Service.slug == candidate).first()
        if other is not None and (ex is None or other.id != ex.id):
            candidate = f"body-{order}-{slugify(title)}"[:180]

        if ex:
            ex.category_id = cat.id
            ex.title = title[:200]
            ex.slug = candidate
            ex.short_description = ""
            ex.price_from = price[:64]
            ex.sort_order = order
            ex.is_active = True
        else:
            db.add(
                Service(
                    category_id=cat.id,
                    title=title[:200],
                    slug=candidate,
                    short_description="",
                    image_url="",
                    price_from=price[:64],
                    sort_order=order,
                    is_active=True,
                    source_item_id=source_key,
                )
            )
        touched += 1

    db.commit()
    return touched


_MANI_PEDI_CATEGORY_ROW = {
    "name": "Mani | Pedi",
    "slug": "mani-pedi",
    "desc": "Manicures, pedicures, gel, spa & combo treatments.",
    "image": site_media_url("mani-pedi.jpg"),
    "sort": 4,
}

_MANI_PEDI_PRICE_LIST: list[tuple[str, int]] = [
    ("Express Manicure", 400),
    ("Classic Manicure", 700),
    ("Spa Manicure", 1000),
    ("Deluxe Manicure", 1200),
    ("Gel Manicure", 1500),
    ("French Manicure", 1200),
    ("Detan Manicure", 900),
    ("Express Pedicure", 500),
    ("Classic Pedicure", 900),
    ("Spa Pedicure", 1300),
    ("Deluxe Pedicure", 1600),
    ("Gel Pedicure", 1700),
    ("French Pedicure", 1400),
    ("Detan Pedicure", 1100),
    ("Callus Removal Pedicure", 1500),
    ("Luxury Spa Pedicure", 2000),
    ("Paraffin Manicure", 1200),
    ("Paraffin Pedicure", 1500),
    ("Manicure + Pedicure Combo", 1800),
    ("Spa Mani + Pedi Combo", 2500),
]


def ensure_mani_pedi_category_and_services(db: Session) -> int:
    """Create Mani | Pedi category if missing and upsert the static INR price list."""
    meta = _MANI_PEDI_CATEGORY_ROW
    cat = db.query(ServiceCategory).filter(ServiceCategory.slug == meta["slug"]).first()
    if cat is None:
        cat = ServiceCategory(
            name=meta["name"],
            slug=meta["slug"],
            image_url=meta["image"],
            description=meta["desc"],
            sort_order=meta["sort"],
            is_active=True,
            reference_url="",
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

    touched = 0
    for order, (title, inr) in enumerate(_MANI_PEDI_PRICE_LIST):
        source_key = f"mani-pedi-manual-{slugify(title)}"[:64]
        price = f"₹{inr}"
        ex = db.query(Service).filter(Service.source_item_id == source_key).first()
        candidate = f"mani-pedi-{slugify(title)}"[:180]
        if candidate == "mani-pedi-":
            candidate = f"mani-pedi-item-{order}"
        other = db.query(Service).filter(Service.slug == candidate).first()
        if other is not None and (ex is None or other.id != ex.id):
            candidate = f"mani-pedi-{order}-{slugify(title)}"[:180]

        if ex:
            ex.category_id = cat.id
            ex.title = title[:200]
            ex.slug = candidate
            ex.short_description = ""
            ex.price_from = price[:64]
            ex.sort_order = order
            ex.is_active = True
        else:
            db.add(
                Service(
                    category_id=cat.id,
                    title=title[:200],
                    slug=candidate,
                    short_description="",
                    image_url="",
                    price_from=price[:64],
                    sort_order=order,
                    is_active=True,
                    source_item_id=source_key,
                )
            )
        touched += 1

    db.commit()
    return touched


_MAKE_UP_CATEGORY_ROW = {
    "name": "Make-Up",
    "slug": "make-up",
    "desc": "Party, bridal, HD & airbrush makeup, hair styling & packages.",
    "image": site_media_url("make-up.jpg"),
    "sort": 5,
}

_MAKE_UP_PRICE_LIST: list[tuple[str, int]] = [
    ("Party Make-Up", 2500),
    ("Engagement Make-Up", 4000),
    ("Reception Make-Up", 5000),
    ("HD Make-Up", 7000),
    ("Airbrush Make-Up", 12000),
    ("Bridal Make-Up (Basic)", 10000),
    ("Bridal Make-Up (HD)", 18000),
    ("Bridal Make-Up (Airbrush)", 25000),
    ("Make-Up Trial", 1500),
    ("Eye Make-Up Only", 800),
    ("Hair Styling (Basic)", 1000),
    ("Hair Styling (Advanced)", 2000),
    ("Saree Draping", 500),
    ("Bridal Package (Make-Up + Hair + Draping)", 20000),
    ("Pre-Bridal Make-Up Package", 15000),
    ("Fashion / Shoot Make-Up", 6000),
    ("Party Make-Up + Hair Combo", 3500),
]


def ensure_make_up_category_and_services(db: Session) -> int:
    """Create Make-Up category if missing and upsert the static INR price list."""
    meta = _MAKE_UP_CATEGORY_ROW
    cat = db.query(ServiceCategory).filter(ServiceCategory.slug == meta["slug"]).first()
    if cat is None:
        cat = ServiceCategory(
            name=meta["name"],
            slug=meta["slug"],
            image_url=meta["image"],
            description=meta["desc"],
            sort_order=meta["sort"],
            is_active=True,
            reference_url="",
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

    touched = 0
    for order, (title, inr) in enumerate(_MAKE_UP_PRICE_LIST):
        source_key = f"make-up-manual-{slugify(title)}"[:64]
        price = f"₹{inr}"
        ex = db.query(Service).filter(Service.source_item_id == source_key).first()
        candidate = f"make-up-{slugify(title)}"[:180]
        if candidate == "make-up-":
            candidate = f"make-up-item-{order}"
        other = db.query(Service).filter(Service.slug == candidate).first()
        if other is not None and (ex is None or other.id != ex.id):
            candidate = f"make-up-{order}-{slugify(title)}"[:180]

        if ex:
            ex.category_id = cat.id
            ex.title = title[:200]
            ex.slug = candidate
            ex.short_description = ""
            ex.price_from = price[:64]
            ex.sort_order = order
            ex.is_active = True
        else:
            db.add(
                Service(
                    category_id=cat.id,
                    title=title[:200],
                    slug=candidate,
                    short_description="",
                    image_url="",
                    price_from=price[:64],
                    sort_order=order,
                    is_active=True,
                    source_item_id=source_key,
                )
            )
        touched += 1

    db.commit()
    return touched


_PRE_BRIDAL_CATEGORY_ROW = {
    "name": "Pre-Bridal",
    "slug": "pre-bridal-service",
    "desc": "Packages, skin, wax, facials, hair & consultation before the wedding.",
    "image": site_media_url("pre-bridal.jpg"),
    "sort": 6,
}

_PRE_BRIDAL_PRICE_LIST: list[tuple[str, int]] = [
    ("Pre-Bridal Basic Package", 5000),
    ("Pre-Bridal Gold Package", 8000),
    ("Pre-Bridal Platinum Package", 12000),
    ("Pre-Bridal Luxury Package", 18000),
    ("Skin Cleanup (Face)", 800),
    ("Basic Facial", 1500),
    ("Advanced Facial (Gold / O3 / Hydra)", 2500),
    ("Full Body Wax", 2500),
    ("Full Body Bleach", 1800),
    ("Face Bleach", 500),
    ("Body Polishing", 3000),
    ("Back Polishing", 1500),
    ("Detan Treatment (Face)", 1200),
    ("Detan Treatment (Full Body)", 2500),
    ("Threading (Eyebrow + Upper Lip)", 100),
    ("Full Face Threading", 300),
    ("Spa Manicure", 1000),
    ("Spa Pedicure", 1300),
    ("Hair Spa", 1500),
    ("Hair Trim / Styling", 800),
    ("Head Massage", 600),
    ("Under Eye Treatment", 800),
    ("Skin Brightening Treatment", 2000),
    ("Acne / Pigmentation Treatment", 2500),
    ("Bridal Consultation Session", 1000),
    ("Pre-Bridal Trial Package", 2000),
]


def ensure_pre_bridal_category_and_services(db: Session) -> int:
    """Create Pre-Bridal category if missing and upsert the static INR price list."""
    meta = _PRE_BRIDAL_CATEGORY_ROW
    cat = db.query(ServiceCategory).filter(ServiceCategory.slug == meta["slug"]).first()
    if cat is None:
        cat = ServiceCategory(
            name=meta["name"],
            slug=meta["slug"],
            image_url=meta["image"],
            description=meta["desc"],
            sort_order=meta["sort"],
            is_active=True,
            reference_url="",
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

    touched = 0
    for order, (title, inr) in enumerate(_PRE_BRIDAL_PRICE_LIST):
        source_key = f"prebridal-manual-{slugify(title)}"[:64]
        price = f"₹{inr}"
        ex = db.query(Service).filter(Service.source_item_id == source_key).first()
        candidate = f"pre-bridal-service-{slugify(title)}"[:180]
        if candidate == "pre-bridal-service-":
            candidate = f"pre-bridal-service-item-{order}"
        other = db.query(Service).filter(Service.slug == candidate).first()
        if other is not None and (ex is None or other.id != ex.id):
            candidate = f"pre-bridal-service-{order}-{slugify(title)}"[:180]

        if ex:
            ex.category_id = cat.id
            ex.title = title[:200]
            ex.slug = candidate
            ex.short_description = ""
            ex.price_from = price[:64]
            ex.sort_order = order
            ex.is_active = True
        else:
            db.add(
                Service(
                    category_id=cat.id,
                    title=title[:200],
                    slug=candidate,
                    short_description="",
                    image_url="",
                    price_from=price[:64],
                    sort_order=order,
                    is_active=True,
                    source_item_id=source_key,
                )
            )
        touched += 1

    db.commit()
    return touched


_ABOUT_PLACEHOLDER_TOKENS = frozenset(
    {
        "",
        "sub",
        "SUB",
        "head",
        "HEAD",
        "p1",
        "p2",
        "lorem",
        "ipsum",
        "test",
        "placeholder",
    }
)


def _is_placeholder_about_text(s: str | None) -> bool:
    t = (s or "").strip()
    if not t:
        return True
    return t.lower() in {x.lower() for x in _ABOUT_PLACEHOLDER_TOKENS}


def ensure_site_settings_about_content(db: Session) -> None:
    """Ensure singleton row id=1 exists; fill missing about copy, brand name, and /site-media images."""
    ss = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    if ss is None:
        db.add(SiteSettings(id=1))
        db.commit()
        ss = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    if ss is None:
        return
    changed = False

    sn = (ss.salon_name or "").strip()
    if not sn or sn.lower() in _LEGACY_SALON_NAMES:
        ss.salon_name = DEFAULT_SALON_NAME[:120]
        changed = True

    if (ss.email or "").strip().lower() == "hello@glamr.com":
        ss.email = DEFAULT_EMAIL
        changed = True
    if not (ss.email or "").strip():
        ss.email = DEFAULT_EMAIL
        changed = True

    p = (ss.phone or "").strip()
    if not p or p == _LEGACY_US_FAKE_PHONE:
        ss.phone = DEFAULT_PHONE
        changed = True

    if not (ss.hours_line or "").strip():
        ss.hours_line = DEFAULT_HOURS_LINE
        changed = True

    if is_legacy_placeholder_address(ss.address):
        ss.address = DEFAULT_ADDRESS
        changed = True

    # Pin for Contact map: only auto-fill when address is the canonical salon line (avoid wrong coords elsewhere).
    if (ss.address or "").strip() == DEFAULT_ADDRESS:
        if not (ss.map_lat or "").strip():
            ss.map_lat = DEFAULT_MAP_LAT
            changed = True
        if not (ss.map_lng or "").strip():
            ss.map_lng = DEFAULT_MAP_LNG
            changed = True

    if _is_placeholder_about_text(ss.about_subtitle):
        ss.about_subtitle = "Beauty, skin & hair under one roof"
        changed = True
    if _is_placeholder_about_text(ss.about_heading):
        ss.about_heading = "Care that shows — from facials to finishing touches"
        changed = True
    if _is_placeholder_about_text(ss.about_para1):
        ss.about_para1 = (
            f"{DEFAULT_SALON_NAME} brings together experienced stylists and skin therapists in a calm, "
            "hygienic space. Whether you need a precision cut, colour refresh, facial, or "
            "a full pre-event glow-up, we listen first and tailor every service to you."
        )
        changed = True
    elif ss.about_para1 and "Glamr" in ss.about_para1:
        ss.about_para1 = ss.about_para1.replace("Glamr", DEFAULT_SALON_NAME).replace("glamr", DEFAULT_SALON_NAME)
        changed = True
    if _is_placeholder_about_text(ss.about_para2):
        ss.about_para2 = (
            "We use trusted professional products, clear pricing, and unhurried appointments "
            "so you always leave feeling confident — never rushed."
        )
        changed = True

    if not (ss.about_main_image or "").strip():
        ss.about_main_image = site_media_url("about-main.jpg")
        changed = True
    if not (ss.about_secondary_image or "").strip():
        ss.about_secondary_image = site_media_url("about-secondary.jpg")
        changed = True
    if not (ss.menu_preview_image or "").strip():
        ss.menu_preview_image = site_media_url("about-secondary.jpg")
        changed = True
    if not (ss.cta_bg_image or "").strip():
        ss.cta_bg_image = site_media_url("cta-bg.jpg")
        changed = True

    if ss.discount_banner_html and "GLAMR20" in ss.discount_banner_html:
        ss.discount_banner_html = ss.discount_banner_html.replace("GLAMR20", "ADORE20")
        changed = True

    if changed:
        db.commit()


def seed_if_empty(db: Session) -> None:
    if db.query(SiteSettings).filter(SiteSettings.id == 1).first() is None:
        db.add(
            SiteSettings(
                id=1,
                salon_name=DEFAULT_SALON_NAME[:120],
                phone=DEFAULT_PHONE,
                email=DEFAULT_EMAIL,
                hours_line=DEFAULT_HOURS_LINE,
                address=DEFAULT_ADDRESS,
                map_lat=DEFAULT_MAP_LAT,
                map_lng=DEFAULT_MAP_LNG,
                discount_banner_html='✨ <strong>Special Offer:</strong> Get 20% off your first visit! Use code <strong>ADORE20</strong>',
                facebook_url="https://facebook.com/",
                instagram_url="https://instagram.com/",
                twitter_url="https://twitter.com/",
                footer_tagline="A premium hair salon dedicated to exceptional service and style.",
                about_subtitle="Beauty, skin & hair under one roof",
                about_heading="Care that shows — from facials to finishing touches",
                about_para1=(
                    f"{DEFAULT_SALON_NAME} brings together experienced stylists and skin therapists in a calm, "
                    "hygienic space. Whether you need a precision cut, colour refresh, facial, or "
                    "a full pre-event glow-up, we listen first and tailor every service to you."
                ),
                about_para2=(
                    "We use trusted professional products, clear pricing, and unhurried appointments "
                    "so you always leave feeling confident — never rushed."
                ),
                about_main_image=site_media_url("about-main.jpg"),
                about_secondary_image=site_media_url("about-secondary.jpg"),
                menu_preview_image=site_media_url("about-secondary.jpg"),
                cta_bg_image=site_media_url("cta-bg.jpg"),
            )
        )
        db.commit()

    ensure_site_settings_about_content(db)

    if db.query(ApiSettings).filter(ApiSettings.id == 1).first() is None:
        db.add(ApiSettings(id=1))
        db.commit()

    if db.query(HeroSlide).count() == 0:
        db.add_all(
            [
                HeroSlide(
                    background_image=site_media_url("hero-01.jpg"),
                    tagline="Confidence Through Great Style",
                    title_line1="LOOK YOUR",
                    title_line2_italic="ABSOLUTE BEST",
                    show_contact_block=True,
                    primary_button_label="Contact Us",
                    primary_button_url="/contact",
                    sort_order=0,
                ),
                HeroSlide(
                    background_image=site_media_url("about-secondary.jpg"),
                    tagline="Expert Care & Styling",
                    title_line1="BEAUTY, STYLE",
                    title_line2_italic="ELEGANCE",
                    show_contact_block=False,
                    primary_button_label="Book Now",
                    primary_button_url="/contact",
                    sort_order=1,
                ),
            ]
        )
        db.commit()

    if db.query(ServiceCategory).count() == 0:
        for row in _ESSENCE_CATALOG_ROWS:
            db.add(
                ServiceCategory(
                    name=row["name"],
                    slug=row["slug"],
                    image_url=row["image"],
                    description=row["desc"],
                    sort_order=row["sort"],
                    is_active=True,
                    reference_url=row.get("reference_url", ""),
                )
            )
        db.commit()

    ensure_essence_main_catalog(db)

    if db.query(GalleryImage).count() == 0:
        urls = [
            site_media_url("about-secondary.jpg"),
            site_media_url("hero-01.jpg"),
            site_media_url("cta-bg.jpg"),
            site_media_url("about-main.jpg"),
            site_media_url("gallery-styling.jpg"),
            site_media_url("skin.jpg"),
        ]
        for i, u in enumerate(urls):
            db.add(GalleryImage(image_url=u, sort_order=i))
        db.commit()

    if db.query(BlogPost).count() == 0:
        db.add(
            BlogPost(
                title="5 Tips for Healthy Winter Hair",
                slug="healthy-winter-hair",
                excerpt="Winter can be harsh on your hair.",
                image_url=site_media_url("hero-01.jpg"),
                body="<p>Winter weather can dry out your hair. Use deep conditioning weekly and protect with a silk-lined hat.</p>",
                author_name="Admin",
                category="Hair Care",
                published_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    if db.query(Testimonial).count() == 0:
        db.add_all(
            [
                Testimonial(
                    quote="I've never been happier with my hair! The team really listened.",
                    author_name="Sarah Jenkins",
                    subtitle="Regular Client",
                    sort_order=0,
                ),
                Testimonial(
                    quote="Truly the best salon in the city. Professional stylists.",
                    author_name="Michael Ross",
                    subtitle="New Client",
                    sort_order=1,
                ),
            ]
        )
        db.commit()

    if db.query(Customer).count() == 0:
        svc = db.query(Service).first()
        c = Customer(
            full_name="Priya Sharma",
            phone="+91 98765 11111",
            email="priya.example@email.com",
            notes="Prefers weekend appointments.",
        )
        db.add(c)
        db.flush()
        lead = db.query(Stylist).filter(Stylist.full_name == "Lead stylist").first()
        if lead is None:
            lead = Stylist(full_name="Lead stylist", sort_order=0, is_active=True)
            db.add(lead)
            db.flush()
        if svc:
            db.add(
                CustomerServiceVisit(
                    customer_id=c.id,
                    service_id=svc.id,
                    visit_date=date.today(),
                    stylist_id=lead.id,
                    amount_charged=svc.price_from,
                    notes="Sample history row linked to a catalog service.",
                )
            )
        else:
            db.add(
                CustomerServiceVisit(
                    customer_id=c.id,
                    service_id=None,
                    custom_service_name="Consultation",
                    visit_date=date.today(),
                    notes="Sample visit without catalog service.",
                )
            )
        db.commit()

    if db.query(SalonProduct).count() == 0:
        db.add_all(
            [
                SalonProduct(
                    name="Professional shampoo (1L)",
                    sku="SHMP-1L",
                    category="Hair care",
                    unit="bottle",
                    quantity_on_hand=12,
                    reorder_level=4,
                    notes="Backbar staple",
                ),
                SalonProduct(
                    name="Tint developer 20 vol",
                    sku="DEV-20",
                    category="Color",
                    unit="bottle",
                    quantity_on_hand=6,
                    reorder_level=3,
                ),
            ]
        )
        db.commit()

    migrate_remote_images_to_site_media(db)
