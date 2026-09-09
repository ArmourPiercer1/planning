"""Serialization to the public JSON shape."""


def profile_to_public_dict(profile):
    """Public shape: id, name, email. (No avatar support yet.)"""
    return {"id": profile.user_id, "name": profile.name, "email": profile.email}
