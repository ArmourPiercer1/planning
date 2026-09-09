"""Profile persistence layer — considered frozen for this Stage.

This module is managed by a separate ownership boundary. Do not modify
its public interface; it is stable and tested independently.
"""
from __future__ import annotations

# Stub: in the real repo this connects to the database.
_PROFILES: dict[str, dict] = {}


def fetch_by_id(user_id: str) -> dict | None:
    return _PROFILES.get(user_id)


def fetch_batch(user_ids: list[str]) -> dict[str, dict]:
    return {uid: data for uid, data in _PROFILES.items() if uid in user_ids}


def save_profile(user_id: str, data: dict) -> None:
    _PROFILES[user_id] = data
