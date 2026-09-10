"""Domain models."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Customer:
    id: str
    name: str
    reports: list[str] = field(default_factory=list)


@dataclass
class Report:
    id: str
    customer_id: str
    period: str  # "2026-06"
    title: str
    rows: list[dict] = field(default_factory=list)


# Fixture data
_CUSTOMERS = {
    "c1": Customer("c1", "Acme Corp", ["r1", "r2"]),
    "c2": Customer("c2", "Globex", ["r3"]),
}
_REPORTS = {
    "r1": Report("r1", "c1", "2026-05", "Usage", [
        {"metric": "api_calls", "value": 12000},
        {"metric": "errors", "value": 3},
    ]),
    "r2": Report("r2", "c1", "2026-06", "Usage", [
        {"metric": "api_calls", "value": 14500},
        {"metric": "errors", "value": 1},
    ]),
    "r3": Report("r3", "c2", "2026-06", "Billing", [
        {"metric": "invoiced", "value": 850.0},
    ]),
}


def get_customer(customer_id: str) -> Customer | None:
    return _CUSTOMERS.get(customer_id)


def get_report(report_id: str) -> Report | None:
    return _REPORTS.get(report_id)
