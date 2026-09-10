"""Core notification send path. No retry today: first non-2xx -> failed."""
from __future__ import annotations

import time
from typing import Any

from .db import NotificationStore
from .provider import ProviderClient, ProviderResponse


def _record_status(response: ProviderResponse, attempts: int) -> str:
    return "sent" if 200 <= response.status < 300 else "failed"


def send_notification(
    store: NotificationStore,
    client: ProviderClient,
    user_id: str,
    template: str,
    variables: dict[str, Any] | None = None,
) -> dict:
    """Send one notification. Returns the stored record."""
    payload = {"to": user_id, "template": template, "vars": variables or {}}
    response = client.send(payload)
    record = {
        "user_id": user_id,
        "template": template,
        "status": _record_status(response, attempts=1),
        "provider_ref": response.body.get("provider_ref"),
        "error": response.body.get("error") if response.status >= 400 else None,
        "attempts": 1,
        "created_at": int(time.time()),
    }
    store.put(record)
    return record
