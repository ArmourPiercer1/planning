# Execution Handoff — stage `config-migration-probe` (P2, p2-v1.1-r1)

Governor decision: **EXECUTE** (`governor-decision.json`, round 3). Audit verdict **PASS**
(round 3, isolated auditor, 0 BLOCKER findings). Plan dir:
`evals/probes/runs/p2-v1.1-r1/plan` (fixture repo: `evals/probes/repos/p2-config-migration`,
repo revision `790b314d1d8780b679c7f585d95c5eb3d2b6640d`).

This handoff stops at the stage boundary (`stage_boundary.stop_after` = [T01, T02] closure
via T03). **No route-specific work may start**: the route (A vs B) is decided by the next
planning stage, whose input is the spike artifact's recommendation line (see "Stage
boundary" below).

## Execution order (from dag.json)

1. **Parallel group 1** — run concurrently with fresh agents:
   - **T01** — run `tasks/T01.json` with a fresh agent; it reads only the package + its
     `required_context.files` (frozen contracts are inlined — the executor never opens
     `stage-contract.json`). Bounded probe, 30–60 min cap, plan-dir artifact only.
   - **T02** — run `tasks/T02.json` with a fresh agent; same rule. New file
     `app/yaml_store.py` + `tests/test_yaml_store.py` (A1 5-item parity matrix).
2. **Parallel group 2 (integration gate last)** — run only after both leaves complete:
   - **T03** — run `tasks/T03.json` with a fresh agent; same rule. Closure task
     (e2e_closure + merged contract_consistency + final_acceptance), owns gate **G1**
     (seam S1, acceptance A1): gates E1 (A1 5-item parity matrix), E2 (full-suite
     regression, DA-1), E3 (spike-artifact acceptance, A4).

Checkpoints: every task has `checkpoint_required: true` (refs `checkpoints/T01.json`,
`checkpoints/T02.json`, `checkpoints/T03.json`). A leaf failure re-runs only that leaf
(parallel group 1 is independent); T03's only integration fix right is a local parity
fix inside `app/yaml_store.py`, recorded as a deviation.

## Executor invariants (frozen — do not re-decide mid-run)

- **C1** (store interface) and **C2** (flat data shape) are frozen and inlined in each
  package; any contract change request goes through the escalation path, not inline edits.
- **DA-1**: `loader.py` / `cli.py` stay on `JsonConfigStore` — byte-identical behavior;
  `tests/test_config.py` (3 tests) must stay green (A3).
- A-1 (flat scalar map) / A-2 (stdlib-only, vendored YAML-subset parser) are frozen
  assumptions; falsification routes to the early planning triggers, not to silent scope
  growth.
- The spike artifact must contain the contractual line
  `Recommendation: Route A` or `Recommendation: Route B` (exactly one, with reasoning) —
  the T01 self-check (AT-T01-2) and the T03 closure check (E3/AT-T03-3) both enforce this
  exact form.

## Deferred findings (from governor-decision.json — intentionally postponed)

- **F01 (MAJOR, POST_STAGE)** — `README.md` context file is not in `snapshot.files`
  because the stage-0 scan enumerates `.py` files only; the file is declared in T01's
  context and listed in `snapshot.unknown_areas`. No execution impact; the route stage's
  stage-0 scan should note scan-observed non-Python files live in `unknown_areas`.
- **F04 (MINOR, OPTIONAL)** — `AT-T02-6` description lacks a marker word (its companion
  evidence is a deterministic unittest invocation). Fix belongs to the next planning pass.

No spikes were ordered (`spikes: []`) — the route question is already the T01 bounded probe.

## Escalation paths

- Blockers → `CONTRACT_CHANGE_REQUEST` / `CORE_SEAM_BLOCKER` via `checkpoint-handoff`
  (record in the task checkpoint; the next checkpoint decision point is the governor's
  call, not the executor's).
- Unhealthy run → **stop-report, no silent continuation** (replan only via the closed
  action set in `replan-controller`; append-only replanning is forbidden).
- Early planning triggers defined in the stage contract: `route_changing_evidence`,
  `frozen_assumption_falsified`, `core_seam_blocker`, `budget_envelope_threatened`.

## Stage boundary (what this stage deliberately does NOT do)

- Route A implementation (YAML primary + `config.json` regenerated export mirror) and
  Route B implementation (full cutover, owned readers updated, `config.json` deleted) are
  **forecast-only** — they have objectives + `depends_on_evidence`, no task DAG.
- When stage acceptance (A1–A4, recorded in `checkpoints/T03.json`) is reached, the normal
  planning trigger `stage_acceptance_reached` fires the **route stage**: it replans with
  the reader list + recommendation from `spike-reader-inventory.md` as its primary input.

## Execution protocol

See `.agents/skills/long-task-planning/references/execution-protocol.md` (checkpoint
writing, worker dispatch, and the governor decision points at checkpoints).

## Provenance

- Full gate history + budget ruling (round-1 in-conversation audit = invalid isolation
  record; accepted full audits = rounds 2–3 = 2/2) in `run-manifest.json`.
- Audit trail: `audit.json` (round 3; rounds 1–2 superseded, retained in git history of
  the run-manifest notes). Governor decisions: `governor-decision.json` (round 3,
  EXECUTE; rounds 1–2 = TARGETED_PATCH, both applied and re-validated).
