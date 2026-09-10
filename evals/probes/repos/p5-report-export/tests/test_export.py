"""CSV export tests."""
from __future__ import annotations

import unittest

from app.services.export import export_csv


class TestCsvExport(unittest.TestCase):
    def test_export_shape(self):
        csv = export_csv("r1")
        self.assertTrue(csv.startswith("metric,value"))
        self.assertIn("api_calls,12000", csv)

    def test_unknown_report(self):
        with self.assertRaises(KeyError):
            export_csv("nope")


if __name__ == "__main__":
    unittest.main()
