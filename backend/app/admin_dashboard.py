"""Aggregate counts for the SQLAdmin home dashboard."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Customer, CustomerServiceVisit, Stylist
from app.visit_pricing import parse_menu_price

# Charts on admin home: distinct customers (≥1 visit that day/week), aligned with “Customers today”.
DASHBOARD_DAILY_CHART_DAYS = 14
DASHBOARD_WEEKLY_CHART_WEEKS = 12


def _week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


@dataclass(frozen=True)
class DashboardStats:
    customer_count: int
    stylist_active_count: int
    customers_seen_today: int
    visits_today: int
    today_sales_total: Decimal
    today_sales_display: str
    as_of_date: date
    daily_customer_chart_labels: tuple[str, ...]
    daily_customer_chart_values: tuple[int, ...]
    weekly_customer_chart_labels: tuple[str, ...]
    weekly_customer_chart_values: tuple[int, ...]


def _daily_distinct_customers_series(db, *, today: date, days: int) -> tuple[tuple[str, ...], tuple[int, ...]]:
    start = today - timedelta(days=days - 1)
    rows = db.execute(
        select(
            CustomerServiceVisit.visit_date,
            func.count(func.distinct(CustomerServiceVisit.customer_id)),
        )
        .where(
            CustomerServiceVisit.visit_date >= start,
            CustomerServiceVisit.visit_date <= today,
        )
        .group_by(CustomerServiceVisit.visit_date)
    ).all()
    by_day = {r[0]: int(r[1]) for r in rows}
    labels: list[str] = []
    values: list[int] = []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        values.append(by_day.get(d, 0))
    return tuple(labels), tuple(values)


def _weekly_distinct_customers_series(db, *, today: date, weeks: int) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """Monday-start weeks; label is week range for readability."""
    this_monday = _week_start_monday(today)
    oldest_monday = this_monday - timedelta(weeks=weeks - 1)
    rows = db.execute(
        select(CustomerServiceVisit.visit_date, CustomerServiceVisit.customer_id).where(
            CustomerServiceVisit.visit_date >= oldest_monday,
            CustomerServiceVisit.visit_date <= today,
        )
    ).all()
    week_sets: defaultdict[date, set[int]] = defaultdict(set)
    for vd, cid in rows:
        week_sets[_week_start_monday(vd)].add(cid)

    labels: list[str] = []
    values: list[int] = []
    wm = oldest_monday
    for _ in range(weeks):
        end_w = wm + timedelta(days=6)
        labels.append(f"{wm.strftime('%d %b')}–{end_w.strftime('%d %b')}")
        values.append(len(week_sets.get(wm, set())))
        wm += timedelta(weeks=1)
    return tuple(labels), tuple(values)


def get_dashboard_stats(*, today: date | None = None) -> DashboardStats:
    """Counts use the server local calendar date for ``visit_date`` (visit rows store date only)."""
    today = today or date.today()
    with SessionLocal() as db:
        customer_count = int(db.scalar(select(func.count(Customer.id))) or 0)
        stylist_active_count = int(
            db.scalar(select(func.count(Stylist.id)).where(Stylist.is_active.is_(True))) or 0
        )
        customers_seen_today = int(
            db.scalar(
                select(func.count(func.distinct(CustomerServiceVisit.customer_id))).where(
                    CustomerServiceVisit.visit_date == today
                )
            )
            or 0
        )
        visits_today = int(
            db.scalar(
                select(func.count(CustomerServiceVisit.id)).where(
                    CustomerServiceVisit.visit_date == today
                )
            )
            or 0
        )
        amounts = db.scalars(
            select(CustomerServiceVisit.amount_charged).where(
                CustomerServiceVisit.visit_date == today
            )
        ).all()
        today_sales_total = sum((parse_menu_price(a) for a in amounts), Decimal(0))

        sym = "₹"
        for a in amounts:
            if a and ("₹" in str(a) or "Rs" in str(a) or "rs" in str(a)):
                sym = "₹"
                break
            if a and "$" in str(a):
                sym = "$"
                break

        if sym == "$":
            today_sales_display = f"{sym}{today_sales_total.quantize(Decimal('0.01'))}"
        elif today_sales_total % 1 == 0:
            today_sales_display = f"{sym}{int(today_sales_total)}"
        else:
            today_sales_display = f"{sym}{today_sales_total.quantize(Decimal('0.01'))}"

        daily_labels, daily_vals = _daily_distinct_customers_series(
            db, today=today, days=DASHBOARD_DAILY_CHART_DAYS
        )
        weekly_labels, weekly_vals = _weekly_distinct_customers_series(
            db, today=today, weeks=DASHBOARD_WEEKLY_CHART_WEEKS
        )

    return DashboardStats(
        customer_count=customer_count,
        stylist_active_count=stylist_active_count,
        customers_seen_today=customers_seen_today,
        visits_today=visits_today,
        today_sales_total=today_sales_total,
        today_sales_display=today_sales_display,
        as_of_date=today,
        daily_customer_chart_labels=daily_labels,
        daily_customer_chart_values=daily_vals,
        weekly_customer_chart_labels=weekly_labels,
        weekly_customer_chart_values=weekly_vals,
    )
