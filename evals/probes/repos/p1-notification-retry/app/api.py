"""HTTP surface (framework-agnostic handler functions)."""
from __future__ import annotations

from .notify import send_notification


def handle_notify(store, client, body: dict) -> tuple[int, dict]:
    """POST /notify  body: {user_id, template, vars}"""
    if "user_id" not in body or "template" not in body:
        return 400, {"error": "user_id and template are required"}
    record = send_notification(
        store, client, body["user_id"], body["template"], body.get("vars")
    )
    return 202, record


def handle_list(store, body: dict) -> tuple[int, dict]:
    """GET /notifications?user_id=..."""
    user_id = body.get("user_id")
    if not user_id:
        return 400, {"error": "user_id is required"}
    return 200, {"notifications": store.for_user(user_id)}
