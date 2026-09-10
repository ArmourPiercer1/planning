"""Existing CSV export."""
from __future__ import annotations

from ..queries import report_with_rows


def export_csv(report_id: str) -> str:
    """Return a CSV string for one report."""
    data = report_with_rows(report_id)
    if data is None:
        raise KeyError(f"unknown report: {report_id}")
    lines = ["metric,value"]
    for row in data["rows"]:
        lines.append(f"{row['metric']},{row['value']}")
    return "\n".join(lines)
