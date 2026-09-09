# Input (verbatim user task)

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

# Repo notes (bounded scan of `candidate/work/repo`)

- `pipeline/producer.py` (9 lines): `make_job(job_id, payload, timeout_ms=30000)`
  returns `{"id", "payload", "timeout_ms"}`. Docstring: "Producer contract:
  the timeout field is 'timeout_ms'."
- `pipeline/engine.py` (12 lines): `run_job(job, work_ms)` reads
  `job.get("timeout_ms", 30000)`; returns `{"id", "status"}` with status
  `"timeout" if work_ms > timeout else "done"`.
- `pipeline/consumer.py` (20 lines): `DEFAULT_TIMEOUT_MS = 30000`;
  `job_timeout(job)` reads `job.get("timeout", DEFAULT_TIMEOUT_MS)` — NOTE in
  source: "the consumer's draft contract expects a 'timeout' key".
  `validate_job(job)` checks presence of `id` and `payload`.
- `tests/test_producer.py`: 2 unittest tests pinning the `timeout_ms` key and
  the 30000 default (green by design).
- `tests/test_consumer.py`: 3 unittest tests pinning the draft `timeout` key
  (`job_timeout({"timeout": 123}) == 123`), the `{}` default (30000), and
  `validate_job` (green by design — they exercise the consumer's own draft
  key, not the producer's output).
- `tests/test_pipeline_e2e.py`: 2 unittest tests.
  `test_pipeline_e2e_effective_timeout` (DESIGNED TO FAIL in baseline:
  producer emits `timeout_ms`, consumer reads `timeout` → effective timeout
  silently falls back to the default).
  `test_pipeline_e2e_engine_timeout` (green: engine boundary at work 50/150
  with timeout 100).
- `pipeline/__init__.py`, `tests/__init__.py`: package markers only.
- No pytest.ini / requirements / config files; tests are stdlib unittest,
  run from the repo root (`python -m unittest ...`).

Diagnosis (baseline): the producer→consumer wire seam (S1) is broken because
`consumer.job_timeout` reads the draft key `timeout` while the producer emits
`timeout_ms`; `engine.run_job` already reads `timeout_ms`, which is why the
engine e2e test is green. The trap: the consumer's own unit test pins the
draft key, so a naive "consumer just reads timeout_ms" change breaks an
existing test unless the draft key is kept as a backward-compatible fallback
or the producer key is renamed (which would break `test_producer.py` and
force an engine change the task forbids).
