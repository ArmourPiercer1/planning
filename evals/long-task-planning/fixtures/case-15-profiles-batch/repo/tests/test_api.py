"""Tests for profile API endpoints."""
from profiles.api import get_profile, get_profiles
from profiles.runtime_state import RequestState


def _reset_state():
    RequestState._TEST_STATE = RequestState()


def test_get_profile():
    _reset_state()
    result = get_profile("u1")
    assert result.user_id == "u1"
    assert result.name == "user-u1"
    assert result.roles == []


def test_get_profiles():
    _reset_state()
    results = get_profiles(["u1", "u2"])
    assert len(results) == 2
    assert results[0].user_id == "u1"
    assert results[1].user_id == "u2"
