"""JSON file config store."""
from __future__ import annotations

import json
from pathlib import Path


class ConfigError(Exception):
    pass


class JsonConfigStore:
    REQUIRED_KEYS = ("app_name", "env", "log_level")

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise ConfigError(f"config file missing: {self.path}")
        self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8"
        )

    def as_dict(self) -> dict:
        return dict(self._data)
