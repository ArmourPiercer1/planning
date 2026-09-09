"""Request handlers (dict in / dict out; no real HTTP layer)."""

from webapp import service
from webapp.serializers import profile_to_public_dict


def handle_update_profile(store, payload):
    """payload: {"user_id": str, "profile_id": str, "fields": dict}.

    Returns {"ok": True, "profile": {...}} or {"ok": False, "error": ...}.
    """
    try:
        profile = service.update_profile(
            store, payload["user_id"], payload["profile_id"], payload.get("fields", {}))
    except PermissionError as e:
        return {"ok": False, "error": "forbidden", "detail": str(e)}
    except (ValueError, KeyError) as e:
        return {"ok": False, "error": "bad-request", "detail": str(e)}
    return {"ok": True, "profile": profile_to_public_dict(profile)}
