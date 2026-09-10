# Execution Handoff — p3-log-rotation (probe run P3-v1.1-r1)

**Plan dir:** `evals/probes/runs/p3-v1.1-r1/plan/`
**Governor decision (final, on the round-2 audit):** `governor-decision.json` → **EXECUTE**. Basis: round-2 **ISOLATED** audit (`fresh_subagent`, `planner_conversation_isolated: true`, `revision_round: 2`, verdict **PASS**) — which superseded the round-1 in-conversation audit (rejected at the isolation gate; its F05 deviation is resolved and kept only as a run-record note). Findings: 0 BLOCKER / 0 MAJOR / 6 MINOR, all deferred: F01–F04 OPTIONAL (marker-regex misses confirmed deterministic), F05 POST_STAGE (resolved process note), F06 OPTIONAL (executor note below). No spikes: `spikes: []` — run execution directly.

**Executor note (F06, from the governor):** evidence commands in the packages/contract that say `pytest <path> -q` must be run with the suite's actual runner — `python -m unittest <dotted.module> -v` (e.g. `python -m unittest tests.test_rotation -v`, `python -m unittest tests.test_log_rotation -v`, `python -m unittest tests.e2e.test_rotation_e2e -v`). The repo is stdlib-only (no pytest dependency); the acceptance criteria themselves are unchanged.

**Repo:** `evals/probes/repos/p3-log-rotation/` at snapshot revision `790b314d1d8780b679c7f585d95c5eb3d2b6640d`.

## Execution order

From `dag.json` parallel groups (integration gate last):

1. **T01** — rotation policy module (`app/rotation.py` + `tests/test_rotation.py`)
2. **T02** — LogWriter rotation wiring (`app/logger.py` + `tests/test_log_rotation.py`) — after T01 (data edge: production import + tests against the real module)
3. **T03** — integration task, runs last: `e2e_closure` with `seam_integration` (owns_fixes_for T01, T02) and `final_acceptance` merged; gate G1 (E1–E4, seams S1+S2, acceptance A6)

Serial plan: T01 → T02 → T03. No parallel groups of > 1 task.

## Task packages

Run each with a **fresh agent**; it reads only the package + its `required_context.files` (frozen contracts are inlined — the executor never opens `stage-contract.json`):

- `tasks/T01.json` — context: `app/logger.py`, `tests/test_log.py`, new `app/rotation.py`, new `tests/test_rotation.py`; contracts C1, C3 inlined with source hashes.
- `tasks/T02.json` — context: `app/logger.py`, `app/server.py`, `tests/test_log.py`, new `app/rotation.py`, new `tests/test_log_rotation.py`; contracts C1, C2, C3 inlined. Upstream: T01's module.
- `tasks/T03.json` — context: `app/server.py`, `app/logger.py`, new `app/rotation.py`, `tests/test_log.py`, new `tests/test_log_rotation.py`, new `tests/e2e/test_rotation_e2e.py`; contracts C1, C2, C3 inlined. Upstream: T01 + T02 outputs and their checkpoints.

Each task completes with a checkpoint at `checkpoints/<id>.json` (checkpoint_required: true in every package).

## Execution protocol

Follow `.agents/skills/long-task-planning/references/execution-protocol.md`.

## Escalation paths

- Blocker found during execution → raise via `checkpoint-handoff` as `CONTRACT_CHANGE_REQUEST` (frozen contract C1/C2/C3 cannot be met as specified) or `CORE_SEAM_BLOCKER` (seam S1/S2 breaks and the integration-only fix in T03's `owns_fixes_for` is insufficient). Do not silently widen scope.
- Unhealthy run (repeated gate failures, runaway context) → stop and report; no silent continuation.
- Replanning is legal only via the governor's `TARGETED_PATCH` route, within `planning_budget` (max 2 full audits, 3 revisions, 5 planning subagents — 1/0/0 used at handoff).

## Stage boundary

Stop after T03 (stage_boundary.stop_after): rotation is a self-contained capability; acceptance A1–A6 are all verified in-stage; no forecast stages are planned. Next planning trigger: `stage_acceptance_reached` (normal) or the early triggers in `stage-contract.json`.
