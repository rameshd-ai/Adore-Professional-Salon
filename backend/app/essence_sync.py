"""Import Hair + Skin price lists from Essence Salon (Respark) public Next.js pages."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Iterator

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Service, ServiceCategory

logger = logging.getLogger(__name__)

REFERENCE_BY_SLUG = {
    "hair": "https://essence-salon.respark.in/essence-salon-193/portblair/hair-srp",
    "skin": "https://essence-salon.respark.in/essence-salon-193/portblair/skin-srp",
}

# Category slugs whose legacy placeholder services (no source_item_id) are dropped on sync.
_DEPRECATED_CATEGORY_SLUGS: frozenset[str] = frozenset()


def fetch_next_data(url: str, timeout: int = 90) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "GlamrCatalogSync/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>([^<]+)</script>', html)
    if not m:
        raise ValueError("No __NEXT_DATA__ in page")
    return json.loads(m.group(1))


def _categories_from_next_data(data: dict[str, Any]) -> list[Any]:
    try:
        return (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialState", {})
            .get("store", {})
            .get("storeData", {})
            .get("categories", [])
        ) or []
    except (TypeError, AttributeError):
        return []


def _best_tree_for_slug(categories: list[Any], slug: str) -> dict[str, Any] | None:
    """
    Essence embeds duplicate names (e.g. two 'Hair' nodes). Pick the node whose
    name matches `slug` and has the richest categoryList.
    """
    slug_l = slug.strip().lower()
    candidates = [
        c
        for c in categories
        if isinstance(c, dict) and (c.get("name") or "").strip().lower() == slug_l
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda c: len(c.get("categoryList") or []))


def _item_id(item: dict[str, Any]) -> str:
    raw = item.get("_id") or item.get("id")
    if raw is None:
        return ""
    if isinstance(raw, dict):
        return str(raw.get("$oid") or raw.get("timestamp") or "")
    return str(raw)


def _price_display(item: dict[str, Any]) -> str:
    sale = item.get("salePrice")
    base = item.get("price")
    try:
        if sale is not None and int(sale) > 0:
            return f"₹{int(sale)}"
    except (TypeError, ValueError):
        pass
    try:
        if base is not None and int(base) > 0:
            return f"₹{int(base)}"
    except (TypeError, ValueError):
        pass
    return "—"


def _walk_subcategory(
    sub: dict[str, Any], top_name: str, path_prefix: str
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    title = (sub.get("name") or "").strip()
    path = f"{path_prefix} › {title}" if path_prefix else title
    for it in sub.get("itemList") or []:
        if it.get("type") != "service":
            continue
        if it.get("active") is False:
            continue
        if it.get("showOnUi") is False:
            continue
        yield top_name, path, it
    for child in sub.get("categoryList") or []:
        yield from _walk_subcategory(child, top_name, path)


def iter_essence_services(top_cat: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    top_name = (top_cat.get("name") or "").strip()
    for sub in top_cat.get("categoryList") or []:
        yield from _walk_subcategory(sub, top_name, "")


def prune_deprecated_placeholder_services(db: Session) -> int:
    """Remove legacy seed rows from categories we no longer maintain (no Essence sync)."""
    if not _DEPRECATED_CATEGORY_SLUGS:
        return 0
    cat_ids = db.scalars(
        select(ServiceCategory.id).where(
            ServiceCategory.slug.in_(_DEPRECATED_CATEGORY_SLUGS)
        )
    ).all()
    if not cat_ids:
        return 0
    r = db.execute(
        delete(Service).where(
            Service.category_id.in_(cat_ids),
            Service.source_item_id.is_(None),
        )
    )
    n = r.rowcount or 0
    if n:
        logger.info("Removed %s legacy placeholder service(s) from deprecated categories", n)
    return n


def sync_essence_hair_skin_services(db: Session) -> int:
    """
    Upsert services for categories slug hair + skin from Essence JSON.
    Returns number of service rows touched (insert + update).
    """
    touched = 0

    for slug, ref in REFERENCE_BY_SLUG.items():
        cat_row = db.scalars(
            select(ServiceCategory).where(ServiceCategory.slug == slug).limit(1)
        ).first()
        if cat_row is None:
            continue
        cat_row.reference_url = ref

        try:
            data = fetch_next_data(ref)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            logger.warning("Essence catalog fetch skipped for %s: %s", slug, e)
            continue

        tree = _best_tree_for_slug(_categories_from_next_data(data), slug)
        if tree is None:
            logger.warning("Essence: no category tree matching slug %r", slug)
            continue

        flat = list(iter_essence_services(tree))
        for order, (_top, path, item) in enumerate(flat):
            sid = _item_id(item)
            if not sid:
                continue
            title = (item.get("name") or "").strip() or "Service"
            desc = (item.get("description") or "").strip()
            short = f"{path}. {desc}".strip(" .") if path else desc
            price = _price_display(item)
            source_key = sid[:64]
            slug_svc = f"e-{source_key}"[:180]

            existing = db.scalars(
                select(Service).where(Service.source_item_id == source_key).limit(1)
            ).first()
            if existing:
                existing.category_id = cat_row.id
                existing.title = title[:200]
                existing.short_description = short[:5000] if short else ""
                existing.price_from = price[:64]
                existing.sort_order = order
                existing.is_active = True
                touched += 1
            else:
                db.add(
                    Service(
                        category_id=cat_row.id,
                        title=title[:200],
                        slug=slug_svc,
                        short_description=(short[:5000] if short else ""),
                        image_url="",
                        price_from=price[:64],
                        sort_order=order,
                        is_active=True,
                        source_item_id=source_key,
                    )
                )
                touched += 1

        # Drop any non-Essence rows in this category (old placeholders, bad slugs, etc.).
        db.execute(
            delete(Service).where(
                Service.category_id == cat_row.id,
                Service.source_item_id.is_(None),
            )
        )

    prune_deprecated_placeholder_services(db)

    db.commit()
    return touched
