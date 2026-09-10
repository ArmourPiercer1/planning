"""Tests for the send path. These must stay green after the retry work."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.db import NotificationStore
from app.provider import ProviderClient, ProviderResponse
from app.notify import send_notification


class OkClient(ProviderClient):
    def send(self, payload: dict) -> ProviderResponse:
        return ProviderResponse(
            status=202, body={"accepted": True, "provider_ref": "ref-1"}
        )


class FailClient(ProviderClient):
    def send(self, payload: dict) -> ProviderResponse:
        return ProviderResponse(status=500, body={"error": "boom"})


class TestSendPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = NotificationStore(Path(self.tmp.name) / "n.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_records_sent(self):
        rec = send_notification(self.store, OkClient(), "u1", "welcome")
        self.assertEqual(rec["status"], "sent")
        self.assertEqual(rec["attempts"], 1)

    def test_failure_records_failed(self):
        rec = send_notification(self.store, FailClient(), "u1", "welcome")
        self.assertEqual(rec["status"], "failed")
        self.assertEqual(rec["error"], "boom")

    def test_record_persisted(self):
        send_notification(self.store, OkClient(), "u1", "welcome")
        self.assertEqual(len(self.store.all()), 1)


if __name__ == "__main__":
    unittest.main()
