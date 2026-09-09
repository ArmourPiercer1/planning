# Task: avatar_url field end-to-end

Add an `avatar_url` field to user profiles, across the whole stack:

1. **Model** (`webapp/models.py`): `Profile` gains `avatar_url` — optional,
   `None` when unset. Existing profiles are created without it.
2. **Validation** (`webapp/validators.py`): when setting `avatar_url`, it
   must be an `https://` URL and at most 2048 characters.
3. **Service + handler** (`webapp/service.py`, `webapp/handlers.py`):
   `avatar_url` is updatable via `update_profile` /
   `handle_update_profile`, and — like name/email — **only the owner may
   set it on their own profile** (the existing ownership rule).
4. **Public JSON** (`webapp/serializers.py`): `profile_to_public_dict`
   includes `avatar_url` **only when it is set** — omit the key entirely
   when absent (no `null`, no empty string).

Existing behavior (name/email, error shapes, serializer keys for existing
profiles) must not change. All existing tests must keep passing; add tests
for: setting avatar (owner), the non-owner rejection, validation failures
(http URL, >2048 chars), and the omission behavior in the public shape.

Repo layout:

```
webapp/
  __init__.py
  models.py        # Profile, ProfileStore
  validators.py    # validate_name, validate_email
  service.py       # create_profile, get_profile, update_profile
  handlers.py      # handle_update_profile(store, payload)
  serializers.py   # profile_to_public_dict(profile)
tests/
  test_webapp.py
```
