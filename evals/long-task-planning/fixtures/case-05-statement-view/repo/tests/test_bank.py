"""Tests for the bank service (all must keep passing)."""

import unittest

from bank.api import Ledger
from bank.views import _iter_api_page, render_statement


class TestApi(unittest.TestCase):
    def test_add_and_list(self):
        l = Ledger()
        l.add("u1", "2026-07-01", 100.0)
        out = l.list_transactions("u1")
        self.assertIn("items", out)
        self.assertIsNone(out["next_cursor"])
        self.assertEqual(len(out["items"]), 1)

    def test_pagination_follows_cursor(self):
        l = Ledger()
        for i in range(5):
            l.add("u1", f"2026-07-0{i + 1}", float(i))
        page1 = l.list_transactions("u1", limit=2)
        self.assertEqual(len(page1["items"]), 2)
        self.assertIsNotNone(page1["next_cursor"])
        page2 = l.list_transactions("u1", cursor=page1["next_cursor"], limit=2)
        self.assertEqual(len(page2["items"]), 2)
        page3 = l.list_transactions("u1", cursor=page2["next_cursor"], limit=2)
        self.assertEqual(len(page3["items"]), 1)
        self.assertIsNone(page3["next_cursor"])

    def test_user_isolation(self):
        l = Ledger()
        l.add("u1", "2026-07-01", 1.0)
        l.add("u2", "2026-07-01", 2.0)
        self.assertEqual(len(l.list_transactions("u1")["items"]), 1)


class TestViews(unittest.TestCase):
    def test_render_statement(self):
        txns = [
            {"id": "t1", "user": "u", "date": "2026-07-01", "amount": 10.0, "kind": "credit"},
            {"id": "t2", "user": "u", "date": "2026-07-02", "amount": 3.0, "kind": "debit"},
        ]
        lines = render_statement(txns)
        self.assertIn("+10.0", lines[0])
        self.assertIn("-3.0", lines[1])

    def test_draft_page_helper_uses_assumed_shape(self):
        # Documents the (unverified) draft assumption shipped in views.py.
        page = {"results": [{"x": 1}], "cursor": "c"}
        self.assertEqual(list(_iter_api_page(page)), [{"x": 1}])


if __name__ == "__main__":
    unittest.main()
