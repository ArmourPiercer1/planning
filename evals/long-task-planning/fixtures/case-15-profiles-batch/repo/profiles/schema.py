"""Shared data schema for profile outputs."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProfileOut:
    """Canonical response shape for profile endpoints."""
    user_id: str
    name: str
    roles: list[str] = ()

    def to_dict(self) -> dict:
        return {"user_id": self.user_id, "name": self.name, "roles": self.roles}
