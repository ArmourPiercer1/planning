"""Startup loading + validation."""
from __future__ import annotations

from .config_store import ConfigError, JsonConfigStore

VALID_LEVELS = ("debug", "info", "warning", "error")


def load_config(path: str) -> dict:
    store = JsonConfigStore(path)
    data = store.as_dict()
    for key in JsonConfigStore.REQUIRED_KEYS:
        if key not in data:
            raise ConfigError(f"missing required config key: {key}")
    if data["log_level"] not in VALID_LEVELS:
        raise ConfigError(f"invalid log_level: {data['log_level']}")
    return data
