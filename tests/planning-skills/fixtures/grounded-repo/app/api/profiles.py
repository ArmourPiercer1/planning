"""Profile lookup routes."""
from app.runtime_state import RequestState
from app.schema import ProfileOut


def lookup_profile(profile_id: str) -> dict:
    state = RequestState()
    row = fetch(profile_id)
    state.values["last_lookup"] = profile_id
    return ProfileOut(id=row["id"], name=row["name"]).as_dict()


def fetch(profile_id: str) -> dict:
    # TODO: serve batch lookups through the shared store
    return {"id": profile_id, "name": "n-" + profile_id}
