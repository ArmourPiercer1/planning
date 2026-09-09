# Execution Handoff — case-06-payslip-summary

- **Plan dir:** `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\out`
- **Repo:** `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\work\repo`
- **Objective:** deterministic 2-decimal payslip summary line + name-sorted `compute_pay` deductions, with tests; all pre-existing tests keep passing.

## Execution order (from `dag.json` parallel groups; integration gates last)

1. **Group 1 (parallel):** `T01` ∥ `T02`
   - `T01` — sort `compute_pay` deductions by name + order test (owns `payroll/calc.py`, `tests/test_payroll.py`)
   - `T02` — summary line in `render_payslip` + exact-format test (owns `payroll/payslip.py`, `tests/test_payslip_summary.py`)
   - Unlocked by frozen contract **C1** (see `dag.json` → `unlock_contracts`).
2. **Group 2:** `T03` — contract-consistency diff vs frozen C1/C2 (owns `tests/test_contract_shape.py`); runs after T01 and T02.
3. **Group 3 (final gate, last):** `T04` — E2E closure + final acceptance, gates **G1** (A3) and **G2** (A5), seams S1/S2; runs after T01, T02, T03. Closes the stage only when the full suite exits 0.

**Critical path:** `T01 -> T03 -> T04`.

## How to run each task

Run each `tasks/<id>.json` with a **fresh agent**; it reads only the package + its `required_context` (never the rest of the plan). A task starts only when all its incoming edges are satisfied (upstream checkpoints exist). Integration tasks consume upstream checkpoints + contracts + changed paths — not the whole repo.

## Escalation paths

- **Blockers** (frozen contract wrong / seam impossible): executor emits `CONTRACT_CHANGE_REQUEST` or `CORE_SEAM_BLOCKER` via the `checkpoint-handoff` skill into `checkpoints/<task-id>.json` and stops; the planning layer decides (V1: no autonomous replan).
- **Unhealthy run** (P80 blown, context churn, repeated gate failures, compactions): stop-report, no silent continuation; only the failed leaf and its downstream subgraph are invalidated (local recoverability).
- **Legal replan actions** for this stage: `split, merge, change_dependency, reduce_scope, checkpoint_and_split, request_contract_revision`.

## Pointer

Execution protocol: `.agents/skills/long-task-planning/references/execution-protocol.md` (startup, freeze discipline A/B/C, checkpoints, unhealthy-run conditions, scheduling, V1 replan boundary).
