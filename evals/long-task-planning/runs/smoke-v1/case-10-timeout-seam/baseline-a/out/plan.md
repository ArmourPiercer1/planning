# Plan: fix the job pipeline timeout defect

Repo: `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\baseline-a\work\repo`
Task: make the whole pipeline work end-to-end (producer → engine **and**
producer → consumer) while keeping every existing unit test green.

## 1. Findings from repo exploration

| Module | Behavior | Timeout key it uses |
|---|---|---|
| `pipeline/producer.py` | `make_job(job_id, payload, timeout_ms=30000)` emits `{"id", "payload", "timeout_ms"}`; docstring (lines 6–7) states the **producer contract key is `timeout_ms`** | `timeout_ms` (emits) |
| `pipeline/engine.py` | `run_job(job, work_ms)` reads `job.get("timeout_ms", 30000)`; returns status `'done'`/`'timeout'` | `timeout_ms` (reads) — matches producer |
| `pipeline/consumer.py` | `job_timeout(job)` reads `job.get("timeout", DEFAULT_TIMEOUT_MS)`; docstring (line 9) admits the **consumer's draft contract expects the `timeout` key**; `validate_job` checks only `id`/`payload` | `timeout` (reads) — **does not match producer** |

Test expectations that pin behavior (all must stay green):

- `tests/test_producer.py` — asserts the **exact** dict equality
  `job == {"id": "j1", "payload": {"cmd": "x"}, "timeout_ms": 500}` and the
  default `timeout_ms == 30000`.
- `tests/test_consumer.py` — asserts `job_timeout({"timeout": 123}) == 123`
  (draft key must keep working) and `job_timeout({}) == 30000`.
- `tests/test_pipeline_e2e.py` — the failing test
  `test_pipeline_e2e_effective_timeout` builds a job via
  `producer.make_job(..., timeout_ms=500)` and calls
  `consumer.job_timeout(job)` **directly on the producer's dict**, expecting
  500. `test_pipeline_e2e_engine_timeout` already passes (engine reads the
  producer's key).

## 2. Root cause (verified empirically)

This is a contract-seam defect, not a logic bug: the producer's wire format
uses `timeout_ms`, while the consumer's draft contract reads a different key,
`timeout`. Producer-built jobs never contain `timeout`, so the consumer's
`.get("timeout", DEFAULT_TIMEOUT_MS)` **silently falls back to the 30000
default** instead of erroring.

Verified baseline by running the full suite from the repo root
(`python -m unittest discover -v`, with `PYTHONDONTWRITEBYTECODE=1` so no
`.pyc` files are written):

- **7 tests: 6 green, 1 red** — exactly as the task states.
- The single failure is
  `tests/test_pipeline_e2e.py::TestPipelineE2E::test_pipeline_e2e_effective_timeout`
  at line 19: `AssertionError: 30000 != 500`.

Each unit suite exercises its own module against its own key, so all unit
tests are green while the end-to-end path producer → consumer is broken. The
producer → engine path is already consistent (both sides use `timeout_ms`)
and must not be touched.

## 3. Key decision: which side adapts to the wire contract

**Decision: the consumer adapts to the producer's wire contract. The
canonical timeout field on the wire is `timeout_ms`; the consumer's
`timeout` key is draft and is demoted to a compatibility fallback.**

Rationale:

1. **The producer is the emitting side, and its contract is settled, not
   draft.** The consumer's own docstring labels its `timeout` key a *draft*
   contract; drafts yield to settled contracts.
2. **The producer's key is independently corroborated by the engine** — a
   second, already-working reader of the same job dict. Treating the
   producer's key as canonical makes producer, engine, and consumer agree on
   one field with **zero changes to the engine/carrier semantics**, which the
   task forbids changing beyond the fix.
3. **The producer cannot adapt.** `test_producer.py` pins the exact output
   dict (`assertEqual` against a 3-key dict), so adding a `timeout` key or
   renaming `timeout_ms` would break a test the task requires to stay green.
   Renaming on "both sides" is explicitly ruled out by the task.
4. **The consumer can adapt without breaking its tests.** Its unit tests
   require `{"timeout": 123} → 123` and `{}` → default, both of which are
   preserved if `timeout` remains as a *fallback* key rather than the
   primary one.
5. **No middle layer can fix it.** The e2e test feeds the producer's dict
   straight into the consumer, so any fix must live inside
   `consumer.job_timeout`. An engine-side or carrier-side translation is out
   of scope per the task.

**Precedence rule when both keys are present:** `timeout_ms` wins (it is the
canonical wire field); `timeout` is a backward-compatibility fallback for
pre-rename jobs; if neither key is present, the existing `DEFAULT_TIMEOUT_MS`
(30000) applies. Behavior for legacy `timeout`-only and keyless jobs stays
byte-identical.

Rejected alternatives:

- *Consumer switches to `timeout_ms` exclusively (drops `timeout`)* — breaks
  `test_consumer.py::test_job_timeout_reads_consumer_key`. Rejected.
- *Producer emits `timeout` instead* — breaks `test_producer.py` exact-dict
  equality and forces an engine change (out of scope). Rejected.
- *Producer emits both keys* — breaks `test_producer.py` exact-dict equality
  (extra key) and leaves two sources of truth. Rejected.
- *Wire adapter between producer and consumer* — the e2e test never passes
  through it, and it adds a component the repo has no place for. Rejected.
- *Change the default or the engine* — neither is broken. Rejected.

## 4. The fix (single function, `pipeline/consumer.py`)

Replace the body/docstring of `job_timeout` with:

```python
def job_timeout(job):
    """Effective timeout (ms) for a job, per the wire contract.

    'timeout_ms' (the producer/engine key) is canonical; 'timeout' is kept
    as a legacy fallback for jobs emitted before the key was settled.
    When both are present, 'timeout_ms' wins.
    """
    return job.get("timeout_ms", job.get("timeout", DEFAULT_TIMEOUT_MS))
```

Precedence: `timeout_ms` > `timeout` > `DEFAULT_TIMEOUT_MS` (30000).
This is the entire code change: one expression in one function in one file.

## 5. Expected test impact

| Test | Input | Expected after fix | Status |
|---|---|---|---|
| `test_producer.py::test_make_job_shape` | `make_job("j1", {"cmd":"x"}, timeout_ms=500)` | exact 3-key dict with `timeout_ms` | green (untouched) |
| `test_producer.py::test_default_timeout` | `make_job("j2", {"cmd":"y"})` | `timeout_ms == 30000` | green (untouched) |
| `test_consumer.py::test_job_timeout_reads_consumer_key` | `job_timeout({"timeout": 123})` | no `timeout_ms` → fallback → 123 | green (fallback preserved) |
| `test_consumer.py::test_job_timeout_default` | `job_timeout({})` | 30000 | green (untouched path) |
| `test_consumer.py::test_validate_job` | shape checks | unchanged | green (untouched) |
| `test_pipeline_e2e.py::test_pipeline_e2e_effective_timeout` | producer job with `timeout_ms=500` → consumer | **500** (was 30000) | red → **green** |
| `test_pipeline_e2e.py::test_pipeline_e2e_engine_timeout` | engine with `timeout_ms=100`, work 50/150 | `done` / `timeout` | green (untouched) |

## 6. What will NOT change (scope guards)

- `pipeline/producer.py` — no key renames, no extra keys (pinned by tests).
- `pipeline/engine.py` — engine/carrier semantics untouched (task rule).
- `pipeline/consumer.py::validate_job` and `DEFAULT_TIMEOUT_MS` — unchanged.
- All files under `tests/` — no test edits of any kind; the e2e test is the
  acceptance criterion.
- No new modules, no wire adapter, no dual-key renames on both sides.

## 7. Verification steps

1. **Edit** `pipeline/consumer.py`: replace `job_timeout` with the version in
   §4. Nothing else in the repo changes.
2. **Run the full suite** from the repo root:
   `python -m unittest discover -v` (or pytest) → expect **7/7 passing**,
   including the previously failing `test_pipeline_e2e_effective_timeout`.
   Baseline reproduced in §2: 6 green + exactly that one red.
3. **Manual spot-checks:**
   - `job_timeout(producer.make_job("j1", {}, timeout_ms=500)) == 500`
   - `job_timeout({"timeout": 123}) == 123` (legacy key still honored)
   - `job_timeout({}) == 30000` (default unchanged)
   - `job_timeout({"timeout_ms": 500, "timeout": 123}) == 500` (precedence)
4. **Final read-only sweep:** confirm by grep that the only remaining users
   of the literal `"timeout"` key are `consumer.py` (fallback) and
   `tests/test_consumer.py` (draft-key test), and that all
   producer/engine/e2e paths use `timeout_ms`. No stray references.

## 8. Risks, edge cases, rollback

- **Job carrying both keys:** deterministic precedence (`timeout_ms` wins),
  documented in the docstring — no ambiguity introduced.
- **Draft-key senders** (any existing producer that emits `timeout`): keep
  working via the fallback, so this is backward compatible.
- **Value semantics:** no type coercion or range validation added — same
  semantics as before the fix; the change only alters *which key is found*,
  per the minimal-fix constraint.
- **Stale comment:** the e2e test's docstring says "DESIGNED TO FAIL in the
  baseline fixture"; after the fix it is stale. It is a comment, not
  behavior — leave it untouched to keep the diff minimal (optional
  follow-up: update the comment).
- **Rollback:** single-function, ~1-line revert in `consumer.py`; no schema
  or state migration involved.
