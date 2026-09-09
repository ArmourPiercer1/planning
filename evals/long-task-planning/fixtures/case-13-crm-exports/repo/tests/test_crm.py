"""Tests for the CRM service (all must keep passing)."""

import unittest

from crm.api import get_contact, list_contacts
from crm.export_v1 import export_v1_json
from crm.storage import ContactStore

SAMPLE = [
    {"id": "c1", "name": "Ada", "email": "ada@x", "tags": ["vip"],
     "tagged_at": "2026-01-01T00:00:00Z"},
    {"id": "c2", "name": "Bo", "email": "bo@x", "tags": [], "tagged_at": None},
]


class TestStorage(unittest.TestCase):
    def test_add_get_all(self):
        s = ContactStore(SAMPLE)
        self.assertEqual(s.get("c1")["name"], "Ada")
        self.assertIsNone(s.get("cX"))
        self.assertEqual(len(s.all()), 2)


class TestApi(unittest.TestCase):
    def setUp(self):
        self.s = ContactStore(SAMPLE)

    def test_list_contacts_v1_shape(self):
        rows = list_contacts(self.s)
        self.assertEqual([r["id"] for r in rows], ["c1", "c2"])
        self.assertEqual(set(rows[0].keys()), {"id", "name", "email"})

    def test_get_contact(self):
        self.assertEqual(get_contact(self.s, "c2")["email"], "bo@x")


class TestExportV1(unittest.TestCase):
    def test_v1_byte_snapshot(self):
        # Physical guard: V1 export bytes are frozen for third parties.
        s = ContactStore(SAMPLE)
        expected = ('{"contacts":[{"email":"ada@x","id":"c1","name":"Ada"},'
                    '{"email":"bo@x","id":"c2","name":"Bo"}],"version":1}')
        self.assertEqual(export_v1_json(s), expected)


if __name__ == "__main__":
    unittest.main()
