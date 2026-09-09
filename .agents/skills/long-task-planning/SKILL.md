---
name: long-task-planning
description: Master pipeline that compiles a bounded, large software engineering task into a verified execution DAG, running the fixed stages Repo Context Snapshot, Stage Contract, context-bounded leaves, typed dependency DAG, integration plan, Task Packages, risk estimates, independent audit. Stage 0 grounds every subsequent claim in a bounded repo scan. Use when the user wants to plan a large multi-agent or multi-round engineering task, asks for an "execution DAG" or "task packages" or "stage plan", or when work is clearly too big for one agent run. NOT for small single-session tasks (under ~1h of work or fewer than 4 leaves), just do those directly.
---

# long-task-planning

Planning Compiler entry point. It runs the **fixed pipeline** below — stages are
not freely reorderable — and hands the executor a plan whose artifacts are
validated by `plan-check.py` (deterministic gate) and by an **independent**
auditor. Shared vocabulary: `../../references/glossary.md`. Schemas:
`../../schemas/planning/`.

## Trigger

- Use when: the task boundary is clear but implementation is large (multi-agent,
  multi-round, many files/layers); the user asks for a plan, DAG, task packages,
  or to "compile this task"; a Stage has failed before due to runaway execution.
- Do NOT use for: tasks an agent can finish in one ~1h run; pure design/brainstorm
  requests (no execution intent); research tasks (use research skills).

**V1 limitation: the repo-grounded pipeline (stages 0–7) only supports Python
repositories.** Stage 0 uses the Python AST for import resolution. For other
languages, the snapshot produces no import graph, and the auditor cannot
verify hidden dependencies. You can still plan with manual repo notes, but
claims of repo-grounded audit require Python.

## Inputs

1. The user task, written **verbatim** to `<plan-dir>/input.md`.
2. Repo scan: run stage 0 first (`repo-context-snapshot` skill) to produce
   `repo-context-snapshot.json` — the bounded file/layer map, one-hop imports,
   shared files, known TODOs. Every later stage reads the snapshot instead of
   re-scanning; the auditor grounds plan claims against it.
3. User constraints (time budget, forbidden changes, dependencies to keep).

`<plan-dir>` convention: `.plans/<stage-id>/` in the target repo (or a path the
user names). Create it before stage 1.

## Procedure (fixed pipeline)

| # | Stage skill | Writes | Gate |
|---|---|---|---|
| 0 | `repo-context-snapshot` | `repo-context-snapshot.json` | plan-check.py validate |
| 1 | `stage-contract` | `stage-contract.json` | `plan-check.py validate` |
| 2 | `context-decomposer` | `candidate-tasks.json` | `plan-check.py validate` |
| 3 | `dependency-dag` | `dag.json` | `plan-check.py validate` |
| 4 | `integration-planner` | `integration-plan.json`, amends `dag.json` | `plan-check.py validate` (both) |
| 5 | `task-packager` | `tasks/<id>.json` | `plan-check.py validate` (each) |
| 6 | `plan-risk-estimator` | `risk-estimates.json`, fills `risk` blocks in packages | `plan-check.py validate` |
| 7 | `plan-auditor` | `audit.json` | verdict PASS |
| 8 | `planning-governor` | `governor-decision.json` | action = EXECUTE |

1. Run stages 0–7 **in order**; each stage reads only the artifacts of earlier
   stages plus the repo (never this conversation's reasoning).
2. After every gate, append to `run-manifest.json` (`pipeline` + `gates`):
   stage name, artifact, gate command, exit code, any fallbacks. A non-zero gate
   exit **stops the pipeline** — do not proceed "with a note".
3. Stage 7 FAIL → **targeted revision loop** (max 3 rounds). Re-run only the
   stage(s) owning the failing checks, then re-audit:

   The revision loop must NOT spawn new reviewers to re-audit; it re-runs only
   the owning stages (per the audit finding → owning stage map below). After
   revision, the **same** auditor re-runs — not a new one. A second full audit
   counts against `planning_budget.max_full_audits` (default 2). When the budget
   is exhausted, the governor routes to `HUMAN_BLOCKER`.

   | Audit check | Owning stage(s) to re-run |
   |---|---|
   | scope_creep, insufficient_non_goals, late_contract_freeze, nondeterministic_acceptance (contract level), open questions | `stage-contract` |
   | hidden_dependency, fake_serialization, ownership_collision, CRITICAL_PATH_INVALID, PARALLEL_GROUP_INCONSISTENT | `dependency-dag` (+ `context-decomposer` if boundaries are wrong) |
   | oversized_leaf, broad_context_loading | `context-decomposer` |
   | hidden_integration_work, NO_INTEGRATION_GATE, SEAM_UNOWNED, INTEGRATION_TASK_NOT_IN_DAG | `integration-planner` |
   | nondeterministic_acceptance (package level), BARE_OBJECTIVE, MISSING_TASK_PACKAGE | `task-packager` |
   | RISK_ESTIMATE_MISSING, oversized without justification | `plan-risk-estimator` |
   | INTEGRATION_KIND_MISSING, HIDDEN_INTEGRATION_WORK, INVALID_INTEGRATION_MERGE | `integration-planner` |
    | CONTRACT_OWNER_TASK_ID, SEAM_PARTICIPANT_TASK_ID, UNBOUND_CONTRACT, UNBOUND_SEAM | `dependency-dag` (binding step) |
    | CONTEXT_FILE_NOT_IN_SNAPSHOT, HIDDEN_DEPENDENCY | `context-decomposer` (closure from snapshot) |
    | STALE_CONTRACT_SNAPSHOT, CONTRACT_NOT_INLINED | `task-packager` (re-run or inline-frozen-contracts.py) |
    | AUDIT_NOT_GROUNDED, AUDIT_SNAPSHOT_MISMATCH | `plan-auditor` (grounding pass) |
    | schema_invalid | the stage that wrote that artifact |
    | over_planning, missing_spike_route | `planning-governor` (route to spike, defer) |

   After 3 FAIL rounds: **stop and escalate to the user** with the full finding
   list. The governor's `forbidden_actions` will include `launch_another_full_audit`
   when the budget is exhausted — do not ignore it. Never ship a FAIL plan.
4. After stage 8 (governor): if `action: EXECUTE` → proceed to handoff.
   If `action: SPIKE` → run spikes, then re-run stages 7-8.
   If `action: TARGETED_PATCH` → fix specific findings, re-audit.
   If `action: HUMAN_BLOCKER` → stop, present to user.
5. On PASS: write the execution handoff (below) into
   `<plan-dir>/HANDOFF.md` and stop. Execution is a different run.

## Execution handoff (on PASS)

The governor's `governor-decision.json` accompanies the handoff: the executor
reads `spikes` to know which bounded probes to run first, and `deferred` to
know which findings are intentionally postponed.

`HANDOFF.md` contains: plan dir path; execution order (parallel groups from
`dag.json`, integration gates last); for each leaf: "run `tasks/<id>.json` with a
fresh agent; it reads only the package + its `required_context.files` (frozen contracts are inlined — the executor never opens `stage-contract.json`"; pointer to the
execution protocol (this skill's `references/execution-protocol.md`); escalation
paths (blockers → `CONTRACT_CHANGE_REQUEST` / `CORE_SEAM_BLOCKER` via
`checkpoint-handoff`; unhealthy run → stop-report, no silent continuation).

## Heuristics

- The pipeline is workflow, not menu: if a stage feels unnecessary for this
  task, the task is probably not a long task — reconsider applying the skill at
  all (see Trigger).
- Prefer fewer, well-bounded leaves over many tiny ones; the decomposer's merge
  rule and the auditor's oversized check are the two-sided constraint.
- A contract that unlocks ≥ 2 parallel tasks is worth freezing explicitly even
  if its spec is short.
- Audit independence matters more than audit speed: always a fresh subagent for
  stage 7. A cheap same-pass "self-audit" is the failure this skill set exists
  to prevent.
- Forecast stages get a stage-level objective and `depends_on_evidence` — no
  detailed DAG, no Task Packages. Producing full packages for uncertain future
  stages is the planning waste this version eliminates.

## Output

`run-manifest.json` (written incrementally; schema
`planning/run-manifest@1`) + `HANDOFF.md` on PASS. Every other artifact is
owned by its stage skill.

## Failure & Escalation

- Gate non-zero → stop pipeline, report which stage/artifact and the gate output.
- 3 audit rounds FAIL → governor routes to HUMAN_BLOCKER (planning budget
  exhausted). Present findings + ask the user (revise input, reduce scope,
  or accept a different Stage boundary).
- Governor action: SPIKE → run bounded probe, re-audit only the affected
  findings. Governor action: TARGETED_PATCH → fix specific findings, re-audit.
- Planning budget exceeded mid-pipeline → governor issues HUMAN_BLOCKER.
  Do not attempt to continue planning; the cost of more meta-work exceeds
  the value. Present to the user.
- Stage skill reports it needs user input (blocking open question) → forward the
  question(s) in one batch to the user; do not guess.
- Any stage discovers the task is not one Stage (scope > budget) → stop and
  propose a Stage split to the user.

## Examples

**Good.** "Add resumable report jobs to this FastAPI service" → 5 leaves + 1
integration task, 3 contracts frozen up front (API, schema, state machine),
parallel group [store ∥ runtime ∥ api], E2E crash-recovery gate explicit,
audit PASS with 2 MINOR findings. Full worked instance:
`../../../../examples/long-task-planning/README.md` (relative to this file).

**Anti-pattern.** Planner runs stages in "whatever order feels right", lets the
auditor run in the same conversation that produced the plan, and on audit FAIL
appends a new task instead of re-running the owning stage. This is exactly the
degenerate behavior the fixed pipeline + independence rule forbid.

Another anti-pattern: the planner runs four full audits, each time spawning a
new reviewer, and the plan grows from 6 to 18 tasks while never starting
execution. The governor's budget enforcement and finding taxonomy prevent this
— EXECUTION_BLOCKER is rare, SPIKE routes empirical questions to probes, and
POST_STAGE items wait until the next stage.
