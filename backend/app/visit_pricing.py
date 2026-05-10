"""Parse price strings and total selected catalog services on a visit."""

from __future__ import annotations

import re
from decimal import Decimal
def parse_menu_price(value: str | None) -> Decimal:
    if not value or not str(value).strip():
        return Decimal(0)
    s = str(value).strip()
    m = re.search(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return Decimal(0)
    try:
        return Decimal(m.group(0).replace(",", ""))
    except Exception:
        return Decimal(0)


def _row_price_str(r: object) -> str:
    return str(getattr(r, "price_from", None) or getattr(r, "price", None) or "")


def format_total_from_sample_prices(rows: list, total: Decimal) -> str:
    if not rows:
        return ""
    sample = next((_row_price_str(r) for r in rows if _row_price_str(r)), "")
    s = str(sample)
    if "₹" in s or "Rs" in s or "rs" in s:
        return f"₹{int(total)}"
    if "$" in s:
        return f"${total.quantize(Decimal('0.01'))}"
    return str(int(total)) if total % 1 == 0 else str(total)


def sum_visit_services(rows: list) -> tuple[Decimal, str]:
    t = sum((parse_menu_price(_row_price_str(r)) for r in rows), Decimal(0))
    return t, format_total_from_sample_prices(rows, t)


def sum_menu_items(rows: list) -> tuple[Decimal, str]:
    """Backward-compatible alias."""
    return sum_visit_services(rows)
