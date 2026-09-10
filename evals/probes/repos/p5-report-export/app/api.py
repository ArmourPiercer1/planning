"""Endpoint handlers (framework-agnostic)."""
from __future__ import annotations

from ..queries import report_with_rows
from ..services.export import export_csv


def handle_export_csv(path_params: dict, body: dict) -> tuple[int, dict]:
    """GET /reports/{id}/export-csv"""
    data = report_with_rows(path_params["id"])
    if data is None:
        return 404, {"error": "unknown report"}
    return 200, {"report_id": data["id"], "csv": export_csv(path_params["id"])}
