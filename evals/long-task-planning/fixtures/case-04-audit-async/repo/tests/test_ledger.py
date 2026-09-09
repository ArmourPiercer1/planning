"""Tests for the ledger service (all must keep passing)."""

import unittest

from ledger.api import AUDIT_EVENT_FIELDS, handle_transfer
from ledger.db import Store
from ledger.events import Bus
from ledger import worker


class TestStore(unittest.TestCase):
    def test_insert_find_all(self):
        s = Store()
        s.insert("t", {"id": 1, "v": "a"})
        s.insert("t", {"id": 2, "v": "b"})
        self.assertEqual(s.find("t", v="b"), [{"id": 2, "v": "b"}])
        self.assertEqual(len(s.all("t")), 2)


class TestBus(unittest.TestCase):
    def test_publish_reaches_subscribers_in_order(self):
        b = Bus()
        seen = []
        b.subscribe("x", lambda e: seen.append(("a", e)))
        b.subscribe("x", lambda e: seen.append(("b", e)))
        b.publish("x", {"n": 1})
        self.assertEqual(seen, [("a", {"n": 1}), ("b", {"n": 1})])

    def test_publish_without_subscribers(self):
        b = Bus()
        self.assertEqual(b.publish("y", {"n": 2}), {"n": 2})


class TestApi(unittest.TestCase):
    def test_transfer_ok_and_audit_written(self):
        store, bus = Store(), Bus()
        out = handle_transfer(store, bus, "acct-a", "acct-b", 10.0)
        self.assertTrue(out["ok"])
        audits = store.all("audit")
        self.assertEqual(len(audits), 1)
        self.assertEqual(set(audits[0].keys()), set(AUDIT_EVENT_FIELDS))
        self.assertEqual(audits[0]["action"], "transfer")

    def test_bad_amount_rejected(self):
        store, bus = Store(), Bus()
        out = handle_transfer(store, bus, "a", "b", -1)
        self.assertFalse(out["ok"])
        self.assertEqual(store.all("audit"), [])


class TestWorker(unittest.TestCase):
    def test_audit_consumer_persists_and_dedupes(self):
        store = Store()
        consume = worker.make_audit_consumer(store)
        ev = {"ts": "t1", "actor": "a", "action": "transfer", "entity": "b", "amount": 1.0}
        self.assertFalse(consume(ev)["deduped"])
        self.assertTrue(consume(dict(ev))["deduped"])
        self.assertEqual(len(store.all("audit")), 1)


if __name__ == "__main__":
    unittest.main()
