"""Event API."""
from __future__ import annotations

from .storage import RingBuffer

_next_id = 0


class EventAPI:
    def __init__(self, capacity: int = 1024):
        self.store = RingBuffer(capacity)

    def post_event(self, payload: dict) -> tuple[int, dict]:
        global _next_id
        _next_id += 1
        eid = f"e{_next_id}"
        self.store.append({"id": eid, **payload})
        return 201, {"id": eid}

    def list_events(self, since: str | None = None) -> tuple[int, dict]:
        items = self.store.read_all()
        if since is not None:
            idx = next((i for i, it in enumerate(items) if it["id"] == since), None)
            if idx is None:
                return 404, {"error": f"unknown since id: {since}"}
            items = items[idx + 1:]
        return 200, {"events": items}
