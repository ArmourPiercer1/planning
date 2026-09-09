# case-10 — trap documentation (NEVER shown to planning subagents)

**Type J — integration-only bug.** The defect exists only at the
producer→consumer seam:

- `producer.make_job` → `{"timeout_ms": ...}`
- `engine.run_job` reads `timeout_ms` (consistent)
- `consumer.job_timeout` reads `timeout` (draft key) → silent fallback to
  30000

Per-side unit tests are all green; `tests/test_pipeline_e2e.py` ships with
**one designed-failing test** (`test_pipeline_e2e_effective_timeout` —
asserts 500, gets 30000). The fixture validator asserts exactly that set
fails. The other e2e test (engine path) passes in the baseline.

What good plans look like:
- Name the canonical wire key and **which side adapts** (the task demands
  the decision be stated; required_contract_change_path marker terms:
  wire contract / seam / adapts / canonical / CONTRACT_CHANGE_REQUEST...).
- The fix is owned by an integration/seam task (or explicitly assigned),
  with the e2e test as acceptance evidence.
- Gates: `seam_integration` (unit-green-e2e-red semantics, key mismatch)
  + `e2e_closure` (effective timeout vs default fallback).

Anti-plans:
- Leaf task "fix consumer key" with no contract decision (marker miss).
- "Fix" the e2e test to expect the default (scope of the fix inverted —
  caught by the gate requiring the effective-timeout semantics).
- Renaming on both sides to a third key (contract churn; judge-pending).
- Ignoring that the engine already matches the producer (A3 is context,
  not a change target — a plan that "fixes" engine.py is adding work).

Special role: **execution-smoke case** (executor runs the plan; the
designed failure is the fixture's proof the trap is real) and **ablation
case** (full-minus-integration: the seam has no owner — measure the
drop).
