# Task: fix the job pipeline timeout defect

In production, downstream consumers apply the **wrong** timeout to jobs.
Every unit test in this repo is green, but the end-to-end test
(`tests/test_pipeline_e2e.py::TestPipelineE2E::test_pipeline_e2e_effective_timeout`)
fails: the effective timeout seen by the consumer is the default, not the
value the producer set.

Your job:

1. Find and fix the defect so the whole pipeline works end-to-end:
   producer → engine **and** producer → consumer.
2. Keep all existing unit tests green;
   `tests/test_pipeline_e2e.py` must go fully green.
3. Decide — and state explicitly in your plan — **which side adapts to the
   wire contract** (producer's `timeout_ms` vs consumer's draft `timeout`
   key). Do not rename keys on both sides without that decision, and do
   not change the simulated carrier/engine semantics beyond the fix.

Repo layout:

```
pipeline/
  __init__.py
  producer.py      # make_job(job_id, payload, timeout_ms=30000)
  engine.py        # run_job(job, work_ms) — uses producer's timeout field
  consumer.py      # job_timeout(job), validate_job(job)
tests/
  test_producer.py        (green)
  test_consumer.py        (green)
  test_pipeline_e2e.py    (one test fails by design in the baseline)
```
