"""Tests for the existing analytics service (all must keep passing)."""

import contextlib
import os
import shutil
import unittest

from analytics import csv_writer, metrics, queries, scheduler


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


class TestMetrics(unittest.TestCase):
    def test_daily_revenue_sums_per_day(self):
        rows = [
            {"date": "2026-07-01", "amount": 10.0},
            {"date": "2026-07-01", "amount": 5.5},
            {"date": "2026-07-02", "amount": 3.0},
        ]
        self.assertEqual(metrics.daily_revenue(rows), {"2026-07-01": 15.5, "2026-07-02": 3.0})

    def test_active_users_counts_distinct(self):
        rows = [
            {"date": "2026-07-01", "user_id": "u1"},
            {"date": "2026-07-01", "user_id": "u1"},
            {"date": "2026-07-01", "user_id": "u2"},
        ]
        self.assertEqual(metrics.active_users(rows), {"2026-07-01": 2})


class TestQueries(unittest.TestCase):
    def test_filter_range_inclusive(self):
        rows = [{"date": d} for d in ("2026-06-28", "2026-06-29", "2026-06-30", "2026-07-01")]
        out = queries.filter_range(rows, "2026-06-29", "2026-06-30")
        self.assertEqual([r["date"] for r in out], ["2026-06-29", "2026-06-30"])

    def test_last_n_days(self):
        self.assertEqual(queries.last_n_days("2026-07-06", 7), ("2026-06-30", "2026-07-06"))


class TestCsvWriter(unittest.TestCase):
    def test_write_csv(self):
        with scratch_dir() as tmp:
            p = os.path.join(tmp, "sub", "out.csv")
            csv_writer.write_csv(p, ["a", "b"], [[1, 2], [3, 4]])
            self.assertTrue(os.path.exists(p))
            with open(p, encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip().splitlines(), ["a,b", "1,2", "3,4"])


class TestScheduler(unittest.TestCase):
    def test_register_and_fire_on_matching_day(self):
        scheduler._JOBS.clear()
        fired = []
        scheduler.register("weekly", "mon 06:00", lambda: fired.append(1))
        self.assertEqual(scheduler.run_jobs_for("2026-07-06", "06:00"), ["weekly"])  # a Monday
        self.assertEqual(fired, [1])

    def test_no_fire_on_other_day(self):
        scheduler._JOBS.clear()
        scheduler.register("weekly", "mon 06:00", lambda: None)
        self.assertEqual(scheduler.run_jobs_for("2026-07-07", "06:00"), [])  # a Tuesday


if __name__ == "__main__":
    unittest.main()
