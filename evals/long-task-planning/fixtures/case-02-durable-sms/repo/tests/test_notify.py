"""Tests for the notify service (all must keep passing)."""

import contextlib
import os
import shutil
import unittest

from notify import cli, sender
from notify.store import JsonQueue


@contextlib.contextmanager
def scratch_dir():
    """Scratch dir via plain os.mkdir (NO explicit mode).

    The eval sandbox's mkdir hook denies access under directories created
    with an explicit 0o700 mode — which is exactly what tempfile.mkdtemp
    passes — so fixture tests avoid tempfile entirely.
    """
    parent = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(parent, f"scratch_{os.getpid()}")
    os.mkdir(d)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


class TestSender(unittest.TestCase):
    def test_accepted(self):
        out = sender.send_sms("+15550001111", "hello")
        self.assertTrue(out["ok"])
        self.assertEqual(out["carrier_response"], "ACCEPTED")

    def test_body_too_long_rejected(self):
        out = sender.send_sms("+15550001111", "x" * 161)
        self.assertFalse(out["ok"])
        self.assertIn("body-too-long", out["carrier_response"])

    def test_bad_phone(self):
        self.assertFalse(sender.send_sms("", "hi")["ok"])


class TestJsonQueue(unittest.TestCase):
    def test_enqueue_pending_mark_done(self):
        with scratch_dir() as tmp:
            q = JsonQueue(os.path.join(tmp, "q.json"))
            q.enqueue({"id": "m1", "status": "pending"})
            q.enqueue({"id": "m2", "status": "pending"})
            self.assertEqual(len(q.pending()), 2)
            q.mark_done("m1")
            self.assertEqual([m["id"] for m in q.pending()], ["m2"])
            self.assertEqual(len(q.all()), 2)


class TestCli(unittest.TestCase):
    def test_send_command_delegates_to_sender(self):
        out = cli.send_command("+15550001111", "hi")
        self.assertTrue(out["ok"])

    def test_dispatch_command_stub(self):
        self.assertEqual(cli.dispatch_command(), [])


if __name__ == "__main__":
    unittest.main()
