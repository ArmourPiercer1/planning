"""Frozen profile store — DO NOT MODIFY during the batch-lookup Stage."""

_PROFILES = {"p-1": "Alice", "p-2": "Bob"}


def get_profile(profile_id: str):
    return {"id": profile_id, "name": _PROFILES.get(profile_id)}
