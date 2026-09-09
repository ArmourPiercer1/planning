"""REST endpoints for user profile lookups."""
from __future__ import annotations

from .runtime_state import RequestState
from .schema import ProfileOut


def get_profile(user_id: str) -> ProfileOut:
    """Fetch a single user profile."""
    state = RequestState.get()
    state.current_user = user_id
    return ProfileOut(user_id=user_id, name=f"user-{user_id}", roles=[])


def get_profiles(user_ids: list[str]) -> list[ProfileOut]:
    """Batch profile lookup — currently loops get_profile() per id.

    TODO: implement proper batch lookup instead of N+1 calls.
    """
    return [get_profile(uid) for uid in user_ids]
