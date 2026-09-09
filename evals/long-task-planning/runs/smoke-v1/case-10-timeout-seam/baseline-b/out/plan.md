# Plan — Fix the job pipeline timeout defect

**Repo:** `work/repo` (`pipeline/` = producer, engine, consumer; `tests/` = 3 test modules).
**Mode:** planning only — no implementation in this run.

## 1. Defect analysis (from the code)

| Component | Timeout behavior | Key used |
|---|---|---|
| `pipeline/producer.py` `make_job` | Emits `timeout_ms` (default 30000) | `timeout_ms` — declared the **producer contract** in the docstring |
| `pipeline/engine.py` `run_job` | `work_ms > job.get("timeout_ms", 30000)` | `timeout_ms` (producer's field) |
| `pipeline/consumer.py` `job_timeout` | `job.get("timeout", 30000)` | `timeout` — explicitly a **draft** contract |

The producer→consumer seam is a key mismatch: the producer emits `timeout_ms`, the consumer reads `timeout`. For every job coming out of `make_job`, the consumer silently falls back to `DEFAULT_TIMEOUT_MS` (30000) instead of the producer-set value. That is the production symptom ("consumers apply the wrong timeout") and the reason the baseline-red test `tests/test_pipeline_e2e.py::TestPipelineE2E::test_pipeline_e2e_effective_timeout` fails (it asserts `consumer.job_timeout(job) == 500` and observes 30000). The other e2e test (`test_pipeline_e2e_engine_timeout`) is green because the engine already reads the producer's field.

Why every unit test is green despite the defect: `test_producer.py` only exercises the producer side, and `test_consumer.py` feeds the consumer its own draft key via hand-built dicts. No existing test crosses the producer→consumer seam — the defect is integration-only.

## 2. Contract decision (explicit)

**The consumer side adapts to the wire contract.** The producer's `timeout_ms` is the canonical wire contract (declared in `producer.py`, already consumed by `engine.py`); the consumer's `timeout` key is an explicitly draft contract.

Decision details:
- `consumer.job_timeout` resolves the effective timeout as: **`timeout_ms` (canonical) → `timeout` (draft, kept for backward compatibility) → `DEFAULT_TIMEOUT_MS` (30000)**.
- **No key rename on either side.** The producer keeps emitting exactly `{"id", "payload", "timeout_ms"}` (byte-identical to today); the engine is untouched, so no carrier/engine semantics change.
- When both keys are present, `timeout_ms` wins (documented in the consumer docstring).
- `DEFAULT_TIMEOUT_MS` stays 30000; `validate_job` is untouched.

Why this side, and not the alternatives:
- **Producer adapts (add or rename to `timeout`):** `test_producer.py::test_make_job_shape` asserts *exact dict equality* on producer output, so adding a key breaks it; renaming the key to `timeout` would additionally break `engine.py`, which reads `timeout_ms`.
- **Both sides rename:** forbidden by the task without this decision, and it would break both unit suites at once.
- **Consumer reads only `timeout_ms`:** breaks `test_consumer.py::test_job_timeout_reads_consumer_key`, which feeds `{"timeout": 123}`.
- The consumer-side dual-key read is the only option that keeps the producer/engine outputs unchanged, keeps all existing unit tests green, **and** makes the e2e test green.

## 3. Phases (ordered)

### Phase 0 — Baseline verification
Rationale: pin the current state before any change, proving the only failure is the seam test (1 red, everything else green). This also captures the "before" state needed for Phase 3's no-change check.
- [ ] Run the full suite from the repo root (`python -m unittest discover -s tests -v`, or `python -m pytest tests/ -v` if pytest is installed).
- [ ] Record the expected baseline: 7 tests — producer 2/2 green, consumer 3/3 green, e2e engine-timeout green, **e2e effective-timeout RED** (30000 vs 500).
- [ ] Snapshot (hash or copy) `pipeline/producer.py` and `pipeline/engine.py` so Phase 3 can prove they were not modified.

### Phase 1 — Implement the fix (consumer side only)
Rationale: the smallest single-file change that realizes the contract decision; keeping the blast radius to one function keeps the diff reviewable.
- [ ] Edit `pipeline/consumer.py::job_timeout` to the dual-key resolution `timeout_ms` → `timeout` → default (per §2), and update its docstring to name the canonical key, the draft fallback, and the precedence rule.
- [ ] Do not touch `DEFAULT_TIMEOUT_MS`, `validate_job`, `pipeline/producer.py`, or `pipeline/engine.py`.

### Phase 2 — Regression coverage for the new seam contract
Rationale: the existing e2e test pins only "consumer sees the producer value"; the precedence/fallback rules we are introducing (both keys present, draft-only, neither) are new behavior and must be pinned so a later "simplification" cannot silently drop the draft fallback or the producer precedence.
- [ ] Add a **new** test file `tests/test_timeout_contract.py` (do not modify existing test files) with four cases: producer job with only `timeout_ms` → producer value; draft job with only `timeout` → draft value; both present → `timeout_ms` wins; neither → 30000.
- [ ] Optionally add one producer-mirror case: `consumer.job_timeout(producer.make_job(..., timeout_ms=T)) == T` — the direct production path.

### Phase 3 — Verify and close
Rationale: the acceptance criteria are "full suite green **and** nothing outside `consumer.py` changed" — verify both halves explicitly, then re-run once as the final gate.
- [ ] Run the full suite; expect all green (7 existing + 4 new = 11).
- [ ] Confirm `pipeline/producer.py` and `pipeline/engine.py` are byte-identical to the Phase 0 snapshots (diff/hash).
- [ ] Re-run the full suite one final time as the closing gate; record results.

## 4. Implementation checklist (explicit step order)

1. Run the full baseline test suite from the repo root; record results (expect 6 green / 1 red: `test_pipeline_e2e_effective_timeout`).
2. Re-confirm the seam analysis (producer emits `timeout_ms`, consumer reads `timeout`, engine reads `timeout_ms`) and freeze the §2 decision: consumer adapts; dual-key read; no key rename on either side.
3. Snapshot the current content of `pipeline/producer.py` and `pipeline/engine.py` (hash or copy) for the final diff check.
4. Edit `pipeline/consumer.py::job_timeout` to the dual-key resolution (`timeout_ms` → `timeout` → default) and update its docstring.
5. Run the consumer unit tests alone — must stay 3/3 green.
6. Add `tests/test_timeout_contract.py` with the four precedence/fallback cases (+ optional producer-mirror case).
7. Run the full suite — expect 11/11 green.
8. Verify `pipeline/producer.py` and `pipeline/engine.py` are unchanged against the Phase 0 snapshots.
9. Final full-suite re-run as the closing gate; record results.

Dependencies (prose):
- **Step 2 happens after step 1** because the baseline run confirms the only failure is the seam test, so the analysis is validated against observed behavior, not just code reading.
- **Step 3 happens before step 4** because the snapshot must be captured before any edit, or the final diff check would compare changed files against themselves.
- **Step 4 happens after step 2** because the exact resolution order and precedence rule are the frozen contract decision; step 4 is its mechanical transcription.
- **Step 5 happens after step 4** because it is the first verification of the changed code, focused on the riskiest existing contract (draft-key backward compatibility), before any new test is written.
- **Step 6 happens after step 5** because the new contract is pinned only after the implementation has been shown to preserve old behavior.
- **Step 7 happens after step 6** because the full-suite gate must include the new seam tests, or it would not verify the precedence rule that was just added.
- **Step 8 happens after step 4** (and is repeated at closing) because it checks the "no engine/carrier semantics change" constraint, which is only at stake once the edit exists.
- **Step 9 happens last** because it is the final acceptance gate after all prior work; if any earlier step failed, we return to the failing step rather than proceeding.

## 5. Testing & verification

Test runner: stdlib `unittest` (tests are `unittest.TestCase`; the repo has no test-runner config). From the repo root:
- Full suite: `python -m unittest discover -s tests -v`
- Or, if pytest is installed: `python -m pytest tests/ -v` (collects the unittest classes identically).

Per-test expectations after the fix:

| Test | Expectation |
|---|---|
| `tests/test_producer.py` (2 tests) | pass — inputs/expectations unchanged |
| `tests/test_consumer.py` (3 tests) | pass — draft-key and default behavior preserved by the fallback chain |
| `tests/test_pipeline_e2e.py::test_pipeline_e2e_effective_timeout` | **pass (was red)** — `consumer.job_timeout` returns 500 for a producer job with `timeout_ms=500` |
| `tests/test_pipeline_e2e.py::test_pipeline_e2e_engine_timeout` | pass — engine semantics untouched |
| `tests/test_timeout_contract.py` (4 new tests) | pass — pins precedence and fallback |

Deterministic acceptance (all must hold):
1. Full suite green: 11/11.
2. `pipeline/producer.py` and `pipeline/engine.py` byte-identical to the pre-fix snapshots.
3. The `pipeline/consumer.py` diff is confined to `job_timeout` (body + docstring); `DEFAULT_TIMEOUT_MS` still 30000; `validate_job` unchanged.
4. The production symptom is resolved: for any `job = make_job(id, payload, timeout_ms=T)`, `consumer.job_timeout(job) == T` (not the default).

## 6. Out of scope

- Renaming or adding keys on the producer side; changing `make_job`'s signature or its 30000 default.
- Any change to `engine.run_job` (comparison semantics, status strings, default lookup) or to the simulated work model.
- Removing the consumer's draft `timeout` key (it stays as a documented fallback until the draft contract is formally retired — a later change, not this fix).
- Changing `DEFAULT_TIMEOUT_MS`, adding `None`/type validation for the timeout fields, or extending `validate_job`.
- Modifying any existing test file (new coverage goes in a new file only).
- Concurrency, retries, persistence, logging, configuration files, new dependencies, or packaging metadata (the repo has none today).
- Routing producer→consumer through the engine: the e2e test calls producer and consumer directly, and no carrier abstraction exists in this repo.
- Documentation beyond the `job_timeout` docstring update.
