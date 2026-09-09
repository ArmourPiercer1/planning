"""Consumer unit tests (green by design — they exercise the consumer's
own draft key, not the producer's output)."""

import unittest

from pipeline import consumer


class TestConsumer(unittest.TestCase):
    def test_job_timeout_reads_consumer_key(self):
        self.assertEqual(consumer.job_timeout({"timeout": 123}), 123)

    def test_job_timeout_default(self):
        self.assertEqual(consumer.job_timeout({}), 30000)

    def test_validate_job(self):
        self.assertTrue(consumer.validate_job({"id": "a", "payload": {}}))
        with self.assertRaises(ValueError):
            consumer.validate_job({})


if __name__ == "__main__":
    unittest.main()
