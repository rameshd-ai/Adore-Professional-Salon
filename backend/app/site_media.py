"""
Bundled public images served at /site-media (see main.py mount).

Run from backend/:  python scripts/fetch_site_media.py
to download sources into backend/site_media/.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

SITE_MEDIA_PREFIX = "/site-media"

# Unsplash photo id (segment after "photo-") -> filename under site_media/
PHOTO_ID_TO_FILE: dict[str, str] = {
    "1503951914875-452162b0f3f1": "hair.jpg",
    "1616394584738-fc6e612e71b9": "skin.jpg",
    "1570172619643-d03a4e73d0de": "skin.jpg",
    "1604654894610-df63bc536371": "nails.jpg",
    "1544161515-4ab6ce6db874": "body.jpg",
    "1516975080664-cc2b4c9f6770": "mani-pedi.jpg",
    "1596462502278-27bfdc403348": "mani-pedi.jpg",
    "1522335789203-aabd1fc54bc9": "make-up.jpg",
    "1519741497674-611481863552": "pre-bridal.jpg",
    "1522337360788-8b13dee7a37e": "about-main.jpg",
    "1595476108010-b4d1f102b1b1": "about-secondary.jpg",
    "1605497788044-5d32c4cacb48": "cta-bg.jpg",
    "1521590832167-7bcbfaa6381f": "cta-bg.jpg",
    "1562322140-8baeececf3df": "hero-01.jpg",
    "1560066984-138dadb4c035": "gallery-styling.jpg",
}

_PHOTO_ID_LOOKUP = {k.lower(): v for k, v in PHOTO_ID_TO_FILE.items()}

_UNSPLASH_RE = re.compile(r"images\.unsplash\.com/photo-([^?&\"'\s>]+)", re.I)

# (filename, full download URL) for scripts/fetch_site_media.py
SITE_MEDIA_DOWNLOADS: list[tuple[str, str]] = [
    ("hair.jpg", "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=1200&q=85"),
    ("skin.jpg", "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=1200&q=85"),
    ("nails.jpg", "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=1200&q=85"),
    ("body.jpg", "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=1200&q=85"),
    ("mani-pedi.jpg", "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=1200&q=85"),
    ("make-up.jpg", "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=1200&q=85"),
    ("pre-bridal.jpg", "https://images.unsplash.com/photo-1519741497674-611481863552?w=1200&q=85"),
    ("about-main.jpg", "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=1200&q=85"),
    ("about-secondary.jpg", "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?w=1200&q=85"),
    ("cta-bg.jpg", "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=1920&q=85"),
    ("hero-01.jpg", "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=1920&q=85"),
    ("gallery-styling.jpg", "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1200&q=85"),
    ("avatar-women-44.jpg", "https://randomuser.me/api/portraits/women/44.jpg"),
    ("avatar-women-68.jpg", "https://randomuser.me/api/portraits/women/68.jpg"),
    ("avatar-men-32.jpg", "https://randomuser.me/api/portraits/men/32.jpg"),
]


def site_media_url(filename: str) -> str:
    name = (filename or "").strip().lstrip("/")
    return f"{SITE_MEDIA_PREFIX}/{name}"


def remote_url_to_site_path(url: str) -> str | None:
    """If url is a known remote catalog image, return /site-media/... else None."""
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if u.startswith(f"{SITE_MEDIA_PREFIX}/"):
        return None
    m = _UNSPLASH_RE.search(u)
    if m:
        key = m.group(1).lower()
        fn = _PHOTO_ID_LOOKUP.get(key)
        if fn:
            return site_media_url(fn)
    if "randomuser.me" in u and "portraits/women/44" in u:
        return site_media_url("avatar-women-44.jpg")
    if "randomuser.me" in u and "portraits/women/68" in u:
        return site_media_url("avatar-women-68.jpg")
    if "randomuser.me" in u and "portraits/men/32" in u:
        return site_media_url("avatar-men-32.jpg")
    if "placehold.co" in u:
        return site_media_url("placeholder-card.svg")
    return None


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def migrate_remote_images_to_site_media(db: Session) -> int:
    """Rewrite known remote image URLs in the DB to /site-media/... paths."""
    from app.models import BlogPost, GalleryImage, HeroSlide, Service, ServiceCategory, SiteSettings

    changed = 0

    def maybe_patch(val: str) -> tuple[str, bool]:
        new = remote_url_to_site_path(val)
        if new and new != val:
            return new, True
        return val, False

    ss = db.query(SiteSettings).filter(SiteSettings.id == 1).first()
    if ss:
        for attr in ("logo_url", "about_main_image", "about_secondary_image", "menu_preview_image", "cta_bg_image"):
            cur = getattr(ss, attr) or ""
            nxt, did = maybe_patch(cur)
            if did:
                setattr(ss, attr, nxt)
                changed += 1

    for cat in db.query(ServiceCategory).all():
        nxt, did = maybe_patch(cat.image_url or "")
        if did:
            cat.image_url = nxt
            changed += 1

    for row in db.query(HeroSlide).all():
        nxt, did = maybe_patch(row.background_image or "")
        if did:
            row.background_image = nxt
            changed += 1

    for row in db.query(Service).all():
        nxt, did = maybe_patch(row.image_url or "")
        if did:
            row.image_url = nxt
            changed += 1

    for row in db.query(GalleryImage).all():
        nxt, did = maybe_patch(row.image_url or "")
        if did:
            row.image_url = nxt
            changed += 1

    for row in db.query(BlogPost).all():
        nxt, did = maybe_patch(row.image_url or "")
        if did:
            row.image_url = nxt
            changed += 1

    if changed:
        db.commit()
    return changed


def ensure_placeholder_asset(site_media_dir: Path) -> None:
    """SVG placeholder when no network photo is available."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <rect width="600" height="400" fill="#eeeeee"/>
  <text x="300" y="205" text-anchor="middle" fill="#666666" font-family="system-ui,sans-serif" font-size="22">Photo soon</text>
</svg>
"""
    path = site_media_dir / "placeholder-card.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(svg, encoding="utf-8")
