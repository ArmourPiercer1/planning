"""Report queries — the single source for fetching report rows.

Everything that needs report data goes through these functions; do not
read _REPORTS from anywhere else.
"""
from __future__ import annotations

from .models import Report, get_customer, get_report


def reports_for_customer(customer_id: str) -> list[Report]:
    cust = get_customer(customer_id)
    if cust is None:
        return []
    return [get_report(rid) for rid in cust.reports if get_report(rid)]


def report_with_rows(report_id: str) -> dict | None:
    rep = get_report(report_id)
    if rep is None:
        return None
    return {
        "id": rep.id,
        "customer_id": rep.customer_id,
        "period": rep.period,
        "title": rep.title,
        "rows": list(rep.rows),
    }
