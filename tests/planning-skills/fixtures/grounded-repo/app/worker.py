"""Background profile refresh worker (existing, unrelated to the batch Stage)."""
from app.runtime_state import RequestState


def refresh_all() -> int:
    state = RequestState()
    state.values["refreshed"] = True
    return 1
