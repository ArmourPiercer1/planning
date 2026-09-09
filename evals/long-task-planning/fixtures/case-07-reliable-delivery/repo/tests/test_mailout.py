"""Tests for the mailout service (all must keep passing)."""

import unittest

from mailout.message import make_message
from mailout.publisher import Publisher
from mailout.queue import MessageQueue
from mailout import worker


class TestPublisher(unittest.TestCase):
    def test_accepted(self):
        self.assertTrue(Publisher().deliver(make_message("m1", "ops@example.com", "hi")))

    def test_unknown_address_rejected(self):
        self.assertFalse(Publisher().deliver(make_message("m1", "x@nowhere", "hi")))

    def test_fail_body_rejected(self):
        self.assertFalse(Publisher().deliver(make_message("m1", "ops@example.com", "FAIL now")))


class TestQueue(unittest.TestCase):
    def test_fifo(self):
        q = MessageQueue([{"id": "a"}, {"id": "b"}])
        q.put({"id": "c"})
        self.assertEqual([m["id"] for m in (q.get(), q.get(), q.get())], ["a", "b", "c"])
        self.assertEqual(q.qsize(), 0)


class TestWorker(unittest.TestCase):
    def setUp(self):
        worker.DROPPED.clear()

    def test_process_and_drop(self):
        q = MessageQueue([
            make_message("m1", "ops@example.com", "ok"),
            make_message("m2", "x@nowhere", "ok"),
        ])
        res = worker.process_queue(Publisher(), q)
        self.assertEqual([r["ok"] for r in res], [True, False])
        self.assertEqual(worker.DROPPED, ["m2"])

    def test_max_items(self):
        q = MessageQueue([make_message(f"m{i}", "ops@example.com", "ok") for i in range(3)])
        res = worker.process_queue(Publisher(), q, max_items=2)
        self.assertEqual(len(res), 2)
        self.assertEqual(q.qsize(), 1)


if __name__ == "__main__":
    unittest.main()
