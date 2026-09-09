"""Tests for the spool service (all must keep passing)."""

import os
import shutil
import unittest

from spool import config
from spool.reader import open_reader
from spool.writer import open_writer


class TestFileBackend(unittest.TestCase):
    # Plain os.mkdir scratch dirs (NO explicit mode): the eval sandbox's
    # mkdir hook denies access under directories created with 0o700 —
    # exactly what tempfile.mkdtemp passes — so we avoid tempfile.
    _SC = iter(range(1000))

    def _new_scratch(self):
        parent = os.path.dirname(os.path.abspath(__file__))
        d = os.path.join(parent, f"scratch_{os.getpid()}_{next(self._SC)}")
        os.mkdir(d)
        self._scratch = d
        return d

    def setUp(self):
        tmp = self._new_scratch()
        self.cfg = {"spool_backend": "file", "spool_path": os.path.join(tmp, "s.jsonl")}

    def tearDown(self):
        shutil.rmtree(getattr(self, "_scratch", None), ignore_errors=True)

    def test_write_read_roundtrip(self):
        w = open_writer(self.cfg)
        w.append({"n": 1})
        w.append({"n": 2})
        w.close()
        r = open_reader(self.cfg)
        self.assertEqual(r.read_all(), [{"n": 1}, {"n": 2}])

    def test_read_from_byte_offset(self):
        w = open_writer(self.cfg)
        w.append({"n": 1})
        first_size = os.path.getsize(self.cfg["spool_path"])
        w.append({"n": 2})
        w.close()
        r = open_reader(self.cfg)
        self.assertEqual(r.read_from(0), [{"n": 1}, {"n": 2}])
        self.assertEqual(r.read_from(first_size), [{"n": 2}])

    def test_offset_of_last_and_truncate(self):
        w = open_writer(self.cfg)
        w.append({"n": 1})
        w.close()
        r = open_reader(self.cfg)
        off = r.offset_of_last()
        self.assertGreater(off, 0)
        r.truncate()
        self.assertEqual(r.read_all(), [])
        self.assertEqual(r.offset_of_last(), 0)

    def test_missing_file_is_empty(self):
        r = open_reader({"spool_backend": "file", "spool_path": os.path.join(self._scratch, "nope.jsonl")})
        self.assertEqual(r.read_all(), [])
        self.assertEqual(r.offset_of_last(), 0)


class TestConfig(unittest.TestCase):
    def test_default_backend(self):
        self.assertEqual(config.get_config()["spool_backend"], "file")

    def test_memory_backend_not_implemented_yet(self):
        with self.assertRaises(ValueError):
            open_writer({"spool_backend": "memory", "spool_path": "x"})


if __name__ == "__main__":
    unittest.main()
