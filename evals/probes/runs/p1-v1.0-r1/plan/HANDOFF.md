# Execution Handoff — p1-retry-v1.0 (P1 baseline probe, v1.0 pipeline)

Plan dir: `evals/probes/runs/p1-v1.0-r1/plan/`
Audit: **PASS** — 2 rounds (round 1 FAIL → targeted revision round 1 → round 2 PASS),
independent auditor path each round (`planner_conversation_isolated: true`),
grounded against `repo-context-snapshot.json` (repo revision 790b314).
Deterministic layer (v1.0 `plan-check.py`): exit 0 — 0 BLOCKER / 0 MAJOR / 22 MINOR.

**Execution is a different run.** This handoff is the stop point of the planning pipeline.

## Execution order (from dag.json)

1. **Parallel group [T01, T02]** — no edge between them (C1/C3 frozen; the 429
   verdict is a plan-validity gate at the integration task, not an execution edge).
2. **T03 (integration, gate G1, seams S1+S2, acceptance A5)** — runs after both.

Critical path: T02 → T03.

## Per-task dispatch

- **T01** — run `tasks/T01.json` with a fresh agent. It reads only the package +
  its `required_context.files` (`app/provider.py`, `tests/test_gateway_observed.py`;
  frozen contracts C1/C3 are inlined — the executor never opens
  `stage-contract.json`). Checkpoint: `checkpoints/T01.json` (required).
- **T02** — run `tasks/T02.json` with a fresh agent. It reads only the package +
  its `required_context.files` (frozen contracts C1/C2/C3 inlined). T02 has **no
  dependency on T01's output** — do not sequence or block it on T01.
  Checkpoint: `checkpoints/T02.json` (required).
- **T03** — run `tasks/T03.json` with a fresh agent after both checkpoints exist.
  It owns the e2e gates E1-E3 and final acceptance A5; integration-only fix
  rights over T01/T02 owned paths (deviations recorded in their checkpoints).
  Checkpoint: `checkpoints/T03.json` (required).

Execution protocol: `evals/probes/baseline-v1.0/skills/long-task-planning/references/execution-protocol.md`.

## Escalation paths

- Blockers surface via `checkpoint-handoff` as `CONTRACT_CHANGE_REQUEST`
  (e.g. T01 verdict FALSIFIED → C1 unfreeze_rule → replan) or
  `CORE_SEAM_BLOCKER`. No silent continuation past a blocker.
- Unhealthy run → stop-report to the orchestrator; do not self-repair the plan.
- Replanning is restricted to the stage contract's `allowed_replan`
  (split, reorder, defer, replace_route, request_contract_revision);
  append-only replanning is forbidden.

## Carried audit warnings (24 MINOR, round 2 — non-gating)

- 22 × `nondeterministic_acceptance` (VAGUE_ACCEPTANCE evidence-marker heuristic):
  acceptance descriptions/evidence in `stage-contract.json` (A1-A5) and
  `tasks/T01-T03.json` acceptance_tests lack the marker wording the lint regex
  expects (e.g. bare `test`/`record`/`status` words). The criteria themselves are
  judgeable: every item names a concrete test, command, or file read.
- 1 × `hidden_integration_work` (T03/omission): `integration-plan.json`
  `omitted_kinds[seam_integration].evidence` still reads "tests/ files all owned
  by T02" — the pre-existing tests/ files belong to no task; the omission itself
  is valid under the new-wiring rule (verified by audit spot check).
- 1 × `hidden_dependency` (T02, intermediate artifact): `candidate-tasks.json`
  T02 `downstream_consumers: []` while the DAG has a T02→T03 verification edge;
  the candidate file is superseded by dag.json + packages for dispatch — no
  execution impact (round-2 auditor note).

Round-1 findings F01 (BLOCKER, T01 hidden dependency) and F24 (MAJOR, T02 phantom
T01 input) are resolved and were re-verified by the round-2 auditor.
