"""Event API tests."""
from __future__ import annotations

import unittest

from app.events import EventAPI


class TestEvents(unittest.TestCase):
    def test_post_returns_id(self):
        api = EventAPI()
        status, body = api.post_event({"kind": "signup", "user": "u1"})
        self.assertEqual(status, 201)
        self.assertIn("id", body)

    def test_list_shape(self):
        api = EventAPI()
        _, first = api.post_event({"kind": "signup"})
        api.post_event({"kind": "login"})
        status, body = api.list_events()
        self.assertEqual(status, 200)
        self.assertEqual(len(body["events"]), 2)

    def test_since_filters(self):
        api = EventAPI()
        _, first = api.post_event({"kind": "a"})
        api.post_event({"kind": "b"})
        _, body = api.list_events(since=first["id"])
        self.assertEqual(len(body["events"]), 1)

    def test_ring_overwrites_oldest(self):
        api = EventAPI(capacity=3)
        for i in range(5):
            api.post_event({"kind": f"k{i}"})
        _, body = api.list_events()
        self.assertEqual(len(body["events"]), 3)
        self.assertEqual([e["kind"] for e in body["events"]], ["k2", "k3", "k4"])


if __name__ == "__main__":
    unittest.main()
