"""Tests for the billing service (all must keep passing)."""

import unittest

from billing import invoice, reports
from billing.store import InvoiceStore


class TestStore(unittest.TestCase):
    def test_add_find_update(self):
        s = InvoiceStore()
        s.add_invoice({"id": "i1", "status": "open"})
        self.assertEqual(s.find("i1")["status"], "open")
        s.update_status("i1", "paid")
        self.assertEqual(s.find("i1")["status"], "paid")
        self.assertIsNone(s.find("nope"))


class TestInvoice(unittest.TestCase):
    def test_make_invoice_shape(self):
        rec = invoice.make_invoice("i1", "acme", 100.0, "2026-07-01")
        self.assertEqual(rec["due"], "2026-07-31")
        self.assertEqual(rec["status"], "open")

    def test_compute_due_states(self):
        rec = invoice.make_invoice("i1", "acme", 100.0, "2026-07-01")
        self.assertEqual(invoice.compute_due(rec, "2026-07-01")["status"], "open")
        self.assertEqual(invoice.compute_due(rec, "2026-07-31")["status"], "due")
        self.assertEqual(invoice.compute_due(rec, "2026-08-04")["days_overdue"], 4)


class TestReports(unittest.TestCase):
    def test_daily_report_rows_and_total(self):
        s = InvoiceStore()
        s.add_invoice(invoice.make_invoice("i1", "acme", 100.0, "2026-07-01"))
        s.add_invoice(invoice.make_invoice("i2", "globex", 50.0, "2026-07-02"))
        out = reports.daily_report(s, "2026-07-01")
        self.assertEqual(len(out["rows"]), 1)
        self.assertEqual(out["total"], 100.0)
        self.assertEqual(out["rows"][0]["customer"], "acme")

    def test_daily_report_empty_day(self):
        s = InvoiceStore()
        self.assertEqual(reports.daily_report(s, "2026-07-01"), {"rows": [], "total": 0.0})


if __name__ == "__main__":
    unittest.main()
