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

## Repo notes (bounded scan)

Repo: `work/repo` — small in-memory job pipeline, stdlib only, unittest-style
tests run with pytest.

| File | Layer | Role |
|---|---|---|
| `pipeline/producer.py` | service | `make_job(job_id, payload, timeout_ms=30000)` → `{"id","payload","timeout_ms"}`; docstring states the producer contract key is `timeout_ms` |
| `pipeline/engine.py` | runtime | `run_job(job, work_ms)` → `{"id","status"}`; reads `job.get("timeout_ms", 30000)`; strict `work_ms > timeout` → status `'timeout'`, else `'done'` |
| `pipeline/consumer.py` | service | `job_timeout(job)` reads `job.get("timeout", 30000)` — a **draft** key `timeout` (NOTE in docstring); `validate_job` checks presence of `id`/`payload`, else `ValueError` |
| `pipeline/__init__.py` | — | package docstring only |
| `tests/test_producer.py` | unit | 2 tests, green; pin the `timeout_ms` shape and the 30000 default |
| `tests/test_consumer.py` | unit | 3 tests, green; pin the draft `timeout` key behavior and `validate_job` |
| `tests/test_pipeline_e2e.py` | e2e | 2 tests; `test_pipeline_e2e_effective_timeout` fails in baseline (`30000 != 500`); the engine e2e case is green |

Defect (physical location of the seam failure): the consumer's draft key
`timeout` vs the producer's wire key `timeout_ms` — invisible to every unit
test, visible only in e2e.

Baseline verified by running the suite on the fixture
(`uv run --no-project --with pytest python -m pytest tests/ -q` from repo root):
`1 failed, 6 passed` — exactly `test_pipeline_e2e_effective_timeout` fails.

Carrier: there is no serializer/transport; the same job dict is passed by
reference between producer, engine, and consumer (simulated carrier).

Known traps:
1. Renaming the key on both sides hides which side was wrong (task forbids it).
2. Engine is a third participant already on the wire key: adapting the
   producer side would force engine + 2 green producer unit tests to change.
3. The existing green consumer unit test `test_job_timeout_reads_consumer_key`
   pins the draft key: a strict single-key consumer switch would force editing
   an existing "green" test, so the decision must keep or replace it
   deliberately (see contract decision DA-1).

## User constraints

- Keep all existing unit tests green; `tests/test_pipeline_e2e.py` fully green.
- State explicitly which side adapts to the wire contract.
- Do not rename keys on both sides; do not change carrier/engine semantics
  beyond the fix.
- Stage override (ablation): integration-planner stage removed — no seam
  census, no integration tasks, no E2E gate tasks, no `owns_fixes_for`;
  `integration-plan.json` is intentionally absent.
