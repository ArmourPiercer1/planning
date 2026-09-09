"""Tests for the webapp profiles (all must keep passing)."""

import unittest

from webapp import handlers, serializers, validators
from webapp.models import ProfileStore
from webapp.service import create_profile, update_profile


class TestValidators(unittest.TestCase):
    def test_name(self):
        with self.assertRaises(ValueError):
            validators.validate_name("   ")
        with self.assertRaises(ValueError):
            validators.validate_name("x" * 121)

    def test_email(self):
        with self.assertRaises(ValueError):
            validators.validate_email("no-at-sign")
        validators.validate_email("a@b.co")  # does not raise


class TestService(unittest.TestCase):
    def setUp(self):
        self.store = ProfileStore()
        create_profile(self.store, "u1", "Ada", "ada@example.com")
        create_profile(self.store, "u2", "Bo", "bo@example.com")

    def test_create_and_get(self):
        self.assertEqual(self.store.get("u1").name, "Ada")

    def test_update_owner(self):
        p = update_profile(self.store, "u1", "u1", {"name": "Ada M."})
        self.assertEqual(p.name, "Ada M.")

    def test_update_non_owner_forbidden(self):
        with self.assertRaises(PermissionError):
            update_profile(self.store, "u2", "u1", {"name": "Hax"})

    def test_update_unknown_field(self):
        with self.assertRaises(ValueError):
            update_profile(self.store, "u1", "u1", {"phone": "1"})


class TestHandler(unittest.TestCase):
    def setUp(self):
        self.store = ProfileStore()
        create_profile(self.store, "u1", "Ada", "ada@example.com")

    def test_handler_ok(self):
        out = handlers.handle_update_profile(self.store, {
            "user_id": "u1", "profile_id": "u1", "fields": {"name": "Ada M."}})
        self.assertTrue(out["ok"])
        self.assertEqual(out["profile"]["name"], "Ada M.")

    def test_handler_forbidden(self):
        out = handlers.handle_update_profile(self.store, {
            "user_id": "someone-else", "profile_id": "u1", "fields": {"name": "X"}})
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "forbidden")


class TestSerializer(unittest.TestCase):
    def test_public_shape(self):
        store = ProfileStore()
        create_profile(store, "u1", "Ada", "ada@example.com")
        d = serializers.profile_to_public_dict(store.get("u1"))
        self.assertEqual(set(d.keys()), {"id", "name", "email"})


if __name__ == "__main__":
    unittest.main()
