"""Log writer tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.logger import LogWriter


class TestLogWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.writer = LogWriter(Path(self.tmp.name) / "app.log")

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_and_read(self):
        self.writer.append("line1")
        self.writer.append("line2")
        self.assertEqual(self.writer.lines(), ["line1", "line2"])

    def test_creates_parent_dirs(self):
        nested = LogWriter(Path(self.tmp.name) / "deep/nested/app.log")
        nested.append("x")
        self.assertTrue((Path(self.tmp.name) / "deep/nested/app.log").exists())


if __name__ == "__main__":
    unittest.main()
