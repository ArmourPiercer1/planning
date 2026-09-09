"""End-to-end pipeline test.

DESIGNED TO FAIL in the baseline fixture: the producer emits 'timeout_ms'
while the consumer reads 'timeout', so the effective timeout silently
falls back to the default. This is the physical demonstration of the
integration-only defect: every unit test above is green.
"""

import unittest

from pipeline import consumer, engine, producer


class TestPipelineE2E(unittest.TestCase):
    def test_pipeline_e2e_effective_timeout(self):
        job = producer.make_job("j1", {"cmd": "x"}, timeout_ms=500)
        self.assertEqual(job["timeout_ms"], 500)
        # consumer must see the producer's timeout, not the default
        self.assertEqual(consumer.job_timeout(job), 500)

    def test_pipeline_e2e_engine_timeout(self):
        job = producer.make_job("j2", {"cmd": "y"}, timeout_ms=100)
        self.assertEqual(engine.run_job(job, 50)["status"], "done")
        self.assertEqual(engine.run_job(job, 150)["status"], "timeout")


if __name__ == "__main__":
    unittest.main()
