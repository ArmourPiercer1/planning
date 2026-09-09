# Long-Task Planning Skills — Architecture & Reference

A "Planning Compiler": compile a **bounded but large** software engineering
task into a **verified execution DAG** of context-bounded Task Packages,
with deterministic gates, an independent audit, and checkpointed execution
handoff. English-first; all artifact keys and finding codes are English.

The skills are live under `.agents/skills/` (the host hot-loads them), shared
assets live under `.agents/` (schemas, scripts, glossary), a complete
end-to-end example under `examples/long-task-planning/`, tests under
`tests/planning-skills/`.

## 1. Why it exists (the failure modes)

Running one long task in one agent conversation degrades in predictable ways:
context grows past the window, compactions lose state, the agent re-reads the
whole repo per subtask, scope creeps, dependencies are prose not structure,
integration is discovered late, and a single failure forces a full restart.
This skill set attacks each mode with **structure, not advice**:

| Failure mode | Structural countermeasure |
|---|---|
| Scope creep | Stage Contract `out_of_scope` with reasons; auditor check `scope_creep` |
| Re-reading the repo per task | Context-closure decomposition; Task Package `required_context` is the *only* context a fresh agent loads |
| Frozen decisions reopened | Contracts freeze at stage 1; changes are `CONTRACT_CHANGE_REQUEST` blockers, not edits |
| Prose dependencies / fake serialization | Typed DAG edges (contract/data/ownership/verification); `fake_serialization_removed` is a required DAG field |
| Integration discovered late | Integration tasks are first-class tasks (T05–T08 pattern) with E2E gates incl. failure scenarios; `NO_INTEGRATION_GATE` is a BLOCKER |
| Oversized leaves | Risk stage with S/M/L/XL rubric + mandatory `oversized_justification`; auditor check |
| One failure restarts everything | Checkpoints at stable subgoals; a failed leaf invalidates only its downstream subgraph |
| Unbounded replanning | Closed replan trigger set + closed legal action set; append-only replanning is explicitly forbidden |
| Planner grades its own homework | Audit runs from a **fresh isolated subagent**; deterministic layer is a fail-closed script |

## 2. Pipeline (fixed 7 stages + execution-time skills)

```
            +-----------------+   validate    +------------------------+
 user task ->| 1 stage-contract |------------->| stage-contract.json    |
            +-----------------+               +------------------------+
                     |  frozen contracts C1..Cn, seams S1..Sm,
                     v  acceptance A1..Ak, budget, allowed_replan
            +-----------------------+   validate    +----------------------+
            | 2 context-decomposer  |-------------> | candidate-tasks.json |
            +-----------------------+               +----------------------+
                     |  leaves by context closure, disjoint owned paths
                     v
            +------------------+   validate    +----------+
            | 3 dependency-dag |-------------> | dag.json |  (typed edges, parallel groups,
            +------------------+               +----------+   critical path, fake-serialization log)
                     v
            +-----------------------+   validate    +----------------------+
            | 4 integration-planner |-------------> | integration-plan.json|  (+ amends dag gates)
            +-----------------------+               +----------------------+
                     v
            +-----------------+   validate   +--------------------+
            | 5 task-packager |-------------> | tasks/T*.json      |
            +-----------------+               +--------------------+
                     v
            +----------------------+   validate   +--------------------+
            | 6 plan-risk-estimator|-------------> | risk-estimates.json| (+ risk blocks in packages)
            +----------------------+               +--------------------+
                     v
            +----------------+  fresh, isolated  +--------------+
            | 7 plan-auditor |<----------------- | audit.json   |
            +----------------+  deterministic + semantic
                     |
          verdict FAIL --> targeted revision (only owning stages re-run,
                     |      max 3 rounds, then stop + user)
          verdict PASS --> HANDOFF (run-manifest + audit.json = the interface)
```

Execution-time skills (not pipeline stages):

- **`checkpoint-handoff`** — every stable subgoal / blocker / stop produces
  `checkpoints/<task-id>.json` (the context handoff: verified facts, changed
  paths, deviations, A/B/C-classified new issues).
- **`replan-controller`** — *interface reserved in V1*: defines the closed
  trigger set (`unhealthy_run`, `blocker`, `gate_failure`, `contract_error`)
  and closed action set; V1 only writes `replan-request.json` and **stops the
  affected branch for a user decision**. No autonomous replan.

The orchestrator (`long-task-planning`) runs the pipeline, enforces the
per-stage `plan-check validate` gates, runs the audit loop with a
**stage-ownership map** (each audit finding type maps to the single stage
that must re-run), and keeps `run-manifest.json` as the incremental gate log.

## 3. Skills

| Skill | Stage | Owns (single-writer) |
|---|---|---|
| `long-task-planning` | orchestrator | pipeline state, run-manifest, HANDOFF |
| `stage-contract` | 1 | `stage-contract.json` (contracts, seams, acceptance, budget, `allowed_replan`) |
| `context-decomposer` | 2 | `candidate-tasks.json` (leaves) |
| `dependency-dag` | 3 | `dag.json` (edges, groups, critical path, `unlock_contracts`, fake-serialization log) |
| `integration-planner` | 4 | `integration-plan.json` (integration tasks T-int, E2E gates) + `dag.json` gate amendments |
| `task-packager` | 5 | `tasks/T*.json` |
| `plan-risk-estimator` | 6 | `risk-estimates.json` + the `risk` block inside each package |
| `plan-auditor` | 7 | `audit.json` (verdict + findings) |
| `checkpoint-handoff` | execution | `checkpoints/T*.json` |
| `replan-controller` | execution (V1 reserved) | `replan-request.json` |

Each `SKILL.md` has the same skeleton: **Trigger / Inputs / Procedure /
Heuristics / Output / Failure & Escalation / Examples** — enforced by
`tests/planning-skills/test_skill_structure.py`.

Shared assets:

- `.agents/references/glossary.md` — single-source vocabulary (Stage, seam,
  closure, ownership collision, A/B/C issue classes, S/M/L/XL rubric, closed
  replan action set, id conventions `T01…/C1…/A1…/S1…/E1…/G1…/F01…`).
- `.agents/schemas/planning/*.schema.json` — 10 schemas, `planning/<kind>@1`.
- `.agents/scripts/plan-check.py` — the deterministic gate (stdlib-only,
  fail-closed, subcommands `validate / lint / report / selftest`).

## 4. Invocation

```
/long-task-planning <task description or file>
```

- Standalone: `/stage-contract <task>` freezes scope for an ad-hoc long task.
- The host hot-loads `.agents/skills/` — no installation step; the skills are
  callable immediately (verified live during build).
- Deterministic checks at any time:

```powershell
# NOTE: sandbox workarounds — use a workspace-local uv cache
$env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"
uv run --no-project python .agents\scripts\plan-check.py validate <artifact.json>
uv run --no-project python .agents\scripts\plan-check.py lint <plan-dir>
uv run --no-project python .agents\scripts\plan-check.py report <plan-dir>
uv run --no-project python .agents\scripts\plan-check.py selftest
```

Full test suite: `pwsh tests\planning-skills\run_all.ps1`.

## 5. Plan-directory artifact map

```
<plan-dir>/
  stage-contract.json     frozen scope, contracts C*, seams S*, acceptance A*, budget
  candidate-tasks.json    leaf tasks T01.. (context closures, disjoint owned_paths)
  dag.json                typed edges, parallel groups, critical path, integration gates G*,
                          unlock_contracts, fake_serialization_removed
  integration-plan.json   integration tasks (contract_consistency / seam_integration /
                          e2e_closure / final_acceptance), E2E gates E* incl. failure scenarios
  risk-estimates.json     S/M/L/XL footprint, P50/P80 ranges, warnings w/ rationale
  tasks/T01..Tnn.json     Task Packages (the ONLY thing an executor reads per task)
  audit-v1.json, audit.json   audit rounds (FAIL → targeted revision → PASS)
  run-manifest.json       pipeline + gate log (incremental)
  checkpoints/T01.json    (execution time) per-task handoff
  replan-request.json     (V1: written + stop, user decides)
```

Id conventions: leaves `T01…`, integration tasks continue the sequence
(`T05…`), contracts `C1…`, acceptance `A1…`, seams `S1…`, E2E gates `E1…`,
integration gates `G1…`, audit findings `F01…`, questions `Q1…`.

## 6. Deterministic gate: finding codes

`plan-check.py lint` is fail-closed (non-zero exit when findings ≥
`--fail-on`, default `BLOCKER`):

| Code | Severity | Meaning |
|---|---|---|
| `SCHEMA_INVALID` | BLOCKER | artifact violates its schema |
| `MISSING_ARTIFACT` / `MISSING_TASK_PACKAGE` / `ORPHAN_TASK_PACKAGE` | BLOCKER | DAG/task/package set mismatch |
| `DUPLICATE_TASK_ID` | BLOCKER | id used twice |
| `DAG_CYCLE` / `DAG_UNKNOWN_TASK` | BLOCKER | graph integrity |
| `CRITICAL_PATH_INVALID` / `PARALLEL_GROUP_INCONSISTENT` | BLOCKER | declared vs computed inconsistency |
| `OWNERSHIP_COLLISION_PARALLEL` | BLOCKER | unordered tasks sharing owned paths |
| `NO_INTEGRATION_GATE` | BLOCKER | no e2e_closure/final_acceptance task |
| `SEAM_UNOWNED` / `INTEGRATION_TASK_NOT_IN_DAG` | BLOCKER | seam or fix-ownership not wired |
| `OPEN_BLOCKING_QUESTION` | BLOCKER | blocking question unresolved before freeze |
| `AUDIT_VERDICT_MISMATCH` | BLOCKER | audit PASS while BLOCKER findings exist |
| `CONTRACT_UNKNOWN` / `CONTRACT_CONSUMED_BEFORE_OWNER` | MAJOR | contract wiring |
| `BARE_OBJECTIVE` | MAJOR | objective shorter than 40 chars or no outcome verb |
| `BROAD_CONTEXT_LOADING` | MAJOR | >25 files or a bare directory as required context |
| `RISK_ESTIMATE_MISSING` | MAJOR | task without a risk entry |
| `UNLOCK_NOT_DECLARED` | MINOR/MAJOR | frozen contract consumed in parallel without an `unlock_contracts` entry |
| `VAGUE_ACCEPTANCE` | MINOR | acceptance text without an observable-evidence marker |

The exit contract: `0` clean · `1` findings ≥ threshold · `2` usage error.

## 7. Executor contract (consumption)

The execution protocol lives in
`.agents/skills/long-task-planning/references/execution-protocol.md`; the
short version:

1. An execution agent starts from **one Task Package file only** (plus the
   files listed in its `required_context`). No other plan artifact, no repo
   archaeology.
2. Context expansion beyond the package (one file at a time, each recorded as
   a `deviation`) is the only legal way in; unbounded reading is an
   unhealthy-run condition.
3. Discovered problems are classified **A** (fix in place, inside owned
   paths), **B** (backlog, record in checkpoint), **C** (blocker:
   `CONTRACT_CHANGE_REQUEST` or `CORE_SEAM_BLOCKER`) — freeze discipline:
   never touch another task's owned paths or a frozen contract.
4. Checkpoint at stable subgoals (commit first, then
   `checkpoints/<task-id>.json` with concrete `verified_facts`).
5. Six unhealthy-run stop conditions (repeated same-failure, context
   bloat, ownership drift, compaction budget, gate thrash, silent scope
   growth) → stop + structured stop-report; in V1 **no autonomous replan** —
   the stop-report feeds `replan-controller`, which writes the request and
   the user decides.

## 8. Evals interface (consumed by the evals bootstrap, not by this repo)

The evals bootstrap (`long_task_planning_evals_bootstrap.md`) scores plans
statically (Layer 1) and runs them dynamically (Layer 2). This repo's
contract toward it:

- **Machine-readable JSON only** — every artifact validates against
  `planning/<kind>@1`; no prose-only plans exist.
- **Stable ids** (`T01…`, `C1…`, `A1…`, `S1…`, `E1…`, `G1…`, `F01…`) so
  scorers can join artifacts across files.
- **Layer 1 scoring maps directly onto artifacts**:
  - contract completeness → `stage-contract.json shared_contracts` (frozen,
    owned, spec);
  - dependency correctness → `dag.json` typed edges (+ `fake_serialization_removed`);
  - ownership collision → `candidate-tasks.json owned_paths` vs `dag.json`
    parallel groups (lint code `OWNERSHIP_COLLISION_PARALLEL`);
  - context locality proxy → `required_context.files` counts (lint code
    `BROAD_CONTEXT_LOADING` threshold 25);
  - integration explicitness → `integration-plan.json` tasks + E2E gates
    incl. failure scenarios;
  - scope discipline → `out_of_scope` entries with reasons;
  - recoverability → per-package `handoff.checkpoint_required` +
    checkpoint schema fields.
- **Dynamic run vector** `E=(success, wall_time, tokens, context_read,
  rework, integration_defects, scope_creep, replans, compactions,
  local_recoverability)` is reconstructable from:
  - `run-manifest.json` (pipeline + gate log = rework/replans/compactions),
  - `checkpoints/T*.json` (`context_read` proxy via `deviations` +
    `changed_paths`; `local_recoverability` = downstream subgraph after a
    failed checkpoint),
  - `audit.json` (integration_defects proxy via `hidden_integration_work`
    findings),
  - execution transcripts (success, wall_time, tokens — outside this repo).
- **Result stability**: `audit.json` carries `verdict` + `findings[]` with
  severity and `revision_round`, so a scorer can distinguish "first-pass
  pass" from "pass after N targeted revisions".

## 9. V2 roadmap (explicitly out of V1)

- **`replan-controller` autonomous** — V1 writes the request and stops; V2
  executes the closed action set under the same invariants (no append-only,
  no contract edits, shrink-only scope changes).
- **`plan-risk-estimator` telemetry** — replace the S/M/L/XL heuristic with
  measured per-leaf compaction counts / context reads from completed runs
  (the checkpoint fields already collect the raw data).
- **`integration-planner` growth** — per-seam failure-scenario generation
  from contract specs; currently the planner authors scenarios by hand and
  the auditor checks coverage.
- **Multi-stage (Stage N+1) chaining** — HANDOFF.md + checkpoints as the
  input contract for the next Stage's `stage-contract`; id sequences continue.
- **Audit sampling** — for very large plans, audit the critical path fully
  and sample parallel leaves.
