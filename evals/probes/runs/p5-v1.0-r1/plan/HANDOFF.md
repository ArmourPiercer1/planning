# Execution Handoff — P5 v1.0 baseline (pdf-export)

- **Plan dir:** `evals/probes/runs/p5-v1.0-r1/plan/`
- **Stage:** `pdf-export` (async monthly PDF export; fixture repo `evals/probes/repos/p5-report-export/`)
- **Audit verdict:** PASS (round 2 of 2; round 1 FAIL → targeted revision round 1 → round 2 PASS). See `audit.json` and `run-manifest.json` for the full record.
- **Execution protocol:** `evals/probes/baseline-v1.0/skills/long-task-planning/references/execution-protocol.md`
- Execution is a different run — this handoff is the complete entry point.

## Execution order (from `dag.json` parallel groups; integration gates last)

1. **Group 1 (parallel):** `T01` (pdf shim + labels) ∥ `T02` (job store + worker) ∥ `T03` (pdf renderer) ∥ `T04` (API endpoints)
2. **Group 2 (parallel):** `T05` (contract consistency pass, read-only) ∥ `T06` (seam integration / composition)
3. **Group 3 (last, integration gates G1-G4):** `T07` (e2e closure + final acceptance A1-A4)

Critical path: `T01 → T05 → T07`. All cross-boundary interfaces (C1-C5) are frozen in
`stage-contract.json` and inlined into the packages, so group 1 tasks run against stubs of
each other's contracts; real-bytes verification is concentrated in T06/T07.

## Per-task start instructions

For each task id, run `tasks/<id>.json` with a **fresh agent**. It reads only the package +
its `required_context.files` (frozen contracts are inlined — the executor never opens
`stage-contract.json`; the inlined specs are hash-verified against the current contract).

- `tasks/T01.json` — shim + labels (context: none; new files only)
- `tasks/T02.json` — job store + worker (context: none; new files only)
- `tasks/T03.json` — renderer (context: `app/queries.py`, `app/models.py` read-only)
- `tasks/T04.json` — API endpoints (context: `app/api.py` to amend, `app/queries.py` + `app/models.py` read-only)
- `tasks/T05.json` — consistency pass (context: the six leaf modules, read-only)
- `tasks/T06.json` — composition (context: all leaf modules)
- `tasks/T07.json` — e2e closure (context: `app/service_app.py`, `app/api.py`, `app/jobs.py`)

Every task has `handoff.checkpoint_required: true`; write `checkpoints/<id>.json` per the
execution protocol before a task is considered done.

## Escalation paths

- **Blockers:** `CONTRACT_CHANGE_REQUEST` (a frozen contract is wrong/insufficient) or
  `CORE_SEAM_BLOCKER` (a seam cannot be closed as specified) — raised via the
  `checkpoint-handoff` skill inside the task's checkpoint; never silently work around a
  frozen contract.
- **Unhealthy run:** stop and write a stop-report (what was tried, where it broke, current
  state). No silent continuation past a repeated gate failure.
- **Budget:** leaf p80 targets per `risk-estimates.json`; a leaf exceeding its p80 should
  checkpoint and apply a legal `allowed_replan` action (split / reorder / change_dependency /
  defer / merge / checkpoint_and_split / reduce_scope) — append-only task growth is not
  allowed.

## Carried audit warnings (MINOR, non-blocking)

- **F68** (nondeterministic_acceptance, cosmetic): `integration-plan.json` gate E3
  `evidence` reads `test_unknown_and_premiere_errors` — a misspelling of the T07 test class
  form (`tests.test_pdf_export.TestErrors` with the same three case names in
  `tasks/T07.json` AT03). The gate remains judgeable from `tasks/T07.json`; align the
  string if the e2e test is being written fresh.
