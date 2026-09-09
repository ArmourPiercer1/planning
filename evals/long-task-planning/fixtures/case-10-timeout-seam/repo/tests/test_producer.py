"""Producer unit tests (green by design)."""

import unittest

from pipeline import producer


class TestProducer(unittest.TestCase):
    def test_make_job_shape(self):
        job = producer.make_job("j1", {"cmd": "x"}, timeout_ms=500)
        self.assertEqual(job, {"id": "j1", "payload": {"cmd": "x"}, "timeout_ms": 500})

    def test_default_timeout(self):
        job = producer.make_job("j2", {"cmd": "y"})
        self.assertEqual(job["timeout_ms"], 30000)


if __name__ == "__main__":
    unittest.main()
