"""JSON-file persistence for notification records."""
from __future__ import annotations

import json
from pathlib import Path


class NotificationStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._records: list[dict] = []
        if self.path.exists():
            self._records = json.loads(self.path.read_text(encoding="utf-8"))

    def put(self, record: dict) -> None:
        self._records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._records, indent=2), encoding="utf-8"
        )

    def all(self) -> list[dict]:
        return list(self._records)

    def for_user(self, user_id: str) -> list[dict]:
        return [r for r in self._records if r["user_id"] == user_id]
