"""Profile service: create / get / update with ownership checks."""

from webapp import validators
from webapp.models import Profile


def create_profile(store, user_id, name, email):
    validators.validate_name(name)
    validators.validate_email(email)
    p = Profile(user_id, name, email)
    store.add(p)
    return p


def get_profile(store, user_id):
    return store.get(user_id)


def update_profile(store, user_id, profile_id, fields):
    """Update name/email on a profile.

    Only the owner (user_id == profile_id) may update. Unknown fields are
    rejected. Returns the updated profile.
    """
    if user_id != profile_id:
        raise PermissionError("only the owner may update this profile")
    profile = store.get(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    allowed = {"name", "email"}
    for k, v in fields.items():
        if k not in allowed:
            raise ValueError(f"field not updatable: {k}")
    if "name" in fields:
        validators.validate_name(fields["name"])
        profile.name = fields["name"]
    if "email" in fields:
        validators.validate_email(fields["email"])
        profile.email = fields["email"]
    return profile
