# Long-Task Planning — Shared Glossary

Single source of truth for terms used by all planning skills in this set and by
downstream consumers (execution agents, evals). Skills must reference terms here
instead of redefining them. Field names in all machine artifacts are English;
this glossary is the only prose definition each term needs.

## Core objects

| Term | Definition |
|---|---|
| **Stage** | A bounded unit of long-task work with a clear objective and deterministic acceptance. One planning run produces exactly one Stage plan. A larger program is a sequence of Stages; this skill set plans one Stage at a time. |
| **Stage Contract** | The frozen, minimal shared agreement that unlocks execution: objective, in/out-of-scope, frozen assumptions and architecture decisions, shared contracts, integration seams, deterministic acceptance, constraints, resource budget, allowed replan actions. Artifact: `stage-contract.json`. |
| **Shared contract** | A cross-task interface that more than one task reads or writes: API signature, data schema, state machine, service interface, error semantics. Each has an `id` (e.g. `C1`), a kind, a spec, and a `logical_owner` naming the responsibility/layer that implements it (not a task id). Contracts are the unit of freezing. |
| **Frozen contract / frozen decision** | A contract or architecture decision that execution agents may use but must not redefine. Changing one is a `CONTRACT_CHANGE_REQUEST`, not an inline edit. |
| **Shared seam** | The exact place where two pieces of work meet: an interface call, a table, a state transition, a startup hook. Seams are what integration gates protect. |
| **Logical owner** | The responsibility or component that implements a shared contract or participates in a seam, named in the Stage Contract (e.g. `api`, `persistence`, `runtime`). Never a task id — task ids don't exist yet. Concrete binding to a leaf happens in the DAG stage. |
| **Binding** | The step in the DAG stage that maps each `logical_owner` to a concrete `owner_task` (via `contract_bindings[]`) and each seam participant role to concrete `participant_tasks` (via `seam_bindings[]`). Rebinding = editing `dag.json` only; the stage contract is never rewritten. |
| **Repo context snapshot** | Stage 0 artifact (`repo-context-snapshot.json`). A bounded, script-generated scan of the repo territory relevant to the Stage: file/layer map, one-hop import graph, known shared files, known seams across layers, TODO/FIXME census. Later stages use it as their repo map — no ad-hoc scanning. The auditor grounds plan claims against it. |
| **Merged kind** | An integration kind satisfied by an integration task whose primary `kind` is different — recorded in that task's `merged_kinds` list (e.g. `final_acceptance` merged into an `e2e_closure` task). The merged kind is not missing; it's satisfied by a multi-purpose task. |
| **Omitted kind** | An integration kind that is deliberately absent from the integration plan, with a structured `omitted_kinds[]` entry carrying a justification (`reason`, ≥ 1 sentence) and `evidence` (≥ 1 concrete reference). Omitting is legitimate only when the plan's facts support it; the new-wiring rule can forbid it. |
| **New-wiring rule** | If any leaf creates a new file (absent from the snapshot) in a directory that already contains another leaf's existing code, new production wiring exists. `seam_integration` cannot be omitted — doing so is `HIDDEN_INTEGRATION_WORK` (BLOCKER). Omitting is only legitimate when the Stage adds no wiring between existing components. |
| **Leaf task** | The smallest schedulable execution unit. Every leaf is a bounded **Task Package** — never a bare "implement X" line. Since @2, each consumed contract is inlined in the package's `frozen_contracts[]` with a full spec and `source_hash`; the executor never opens `stage-contract.json`. |
| **Task Package** | The self-contained brief an execution agent needs to start a leaf: required context, inputs, frozen contracts, owned paths, non-goals, constraints, deliverables, acceptance tests, failure cases, integration dependency, handoff/checkpoint requirements, and an inline risk estimate. Artifact: `tasks/<id>.json`. |
| **Context closure** | The minimal set of files, contracts, and concepts an agent must load to complete a task. Decomposition boundaries are drawn by context closure, not by feature/module/directory. |
| **Owned path** | A file or directory a task may create/modify. Parallel tasks must have disjoint owned paths; otherwise that is an ownership collision. |
| **Responsibility layer** | A functional stratum of the system, e.g. `ui`, `store`, `api`, `service`, `runtime`, `persistence`, `lifecycle`, `e2e`. A leaf crossing too many layers is oversized. |

## Execution DAG

| Term | Definition |
|---|---|
| **Execution DAG** | The directed acyclic graph of leaf tasks under real semantic dependencies. Markdown section order is never an execution order. |
| **Dependency types** | `contract` (task consumes a contract another task owns or finalizes), `data` (task consumes concrete output — files, rows, binaries — produced by another task), `ownership` (tasks would touch the same path and must be ordered), `verification` (task exists to verify others, e.g. an integration gate). Every edge carries a `reason` and exactly one type. |
| **Critical path** | The longest chain of dependent tasks; it bounds Stage wall time under unbounded parallelism. Optimized to be short, not to maximize concurrency. |
| **Parallel group** | A set of tasks with no unsatisfied dependency between them and disjoint owned paths. |
| **Fake serialization** | A dependency that exists only because requirements were written in that order (or tasks share a name), with no contract/data/ownership/verification reason. Must be detected and removed. |
| **Ownership collision** | Two tasks in the same parallel group (i.e. unordered) whose owned paths overlap. Hazardous unless the overlap is proven read-only for at least one side. |
| **Integration gate** | An explicit task (never an assumption) that verifies seams after the leaves it covers complete: contract consistency check, seam integration, E2E closure, final acceptance. |
| **Local recoverability** | The property that any single leaf failure only invalidates that leaf and its downstream subgraph — never the whole Stage. A plan lacking it is a planning defect. |

## Freeze discipline (execution-time)

When an execution agent finds a problem mid-run, exactly one of:

| Class | Meaning | Handling |
|---|---|---|
| **A** | Must be fixed to complete the current task. | Fix inside the current task; record in checkpoint `deviations`. |
| **B** | Worth improving, does not block Stage closure. | Record in checkpoint `newly_discovered_issues` as `backlog`. Never implement. |
| **C** | The frozen contract/architecture itself is wrong; the task cannot be implemented correctly as specified. | Stop out-of-scope implementation. Emit a `CONTRACT_CHANGE_REQUEST` (contract-level change) or `CORE_SEAM_BLOCKER` (a seam cannot be built at all) into the checkpoint; hand back to the planning layer. |

- **CONTRACT_CHANGE_REQUEST** — structured request: which contract id, what change, why the current spec is wrong, evidence, proposed new spec. Decided by the planning layer, never by the executor.
- **CORE_SEAM_BLOCKER** — a seam is structurally impossible under the current architecture; requires replan (often `replace_route`).

## Unhealthy-run termination conditions

A leaf run must stop normal implementation and emit a structured stop-report
(minimal reproducer, current diagnosis, failed attempts, blocker, evidence,
recommended split/escalation) when any of:

1. Well past P80 with no approach to closure.
2. Context churn keeps growing (reads expanding beyond `required_context` repeatedly).
3. New cross-layer dependencies keep appearing.
4. Multiple compactions already occurred or are clearly imminent.
5. Three consecutive implementation attempts fail the same acceptance gate.
6. The task is forced to read far more than its Required Context.

## Size and cost heuristics (guidelines, not SLAs)

| Signal | Value | Meaning |
|---|---|---|
| Leaf P50 | ~30–60 min | Comfortable single-run size. |
| Leaf P80 | ≤ 90 min | Target; beyond it, question the boundary. |
| Expected compactions ≥ 4 | — | Mandatory re-split check. |
| Expected compactions ≥ 10 | — | Presumed planning failure. |
| Footprint | `S / M / L / XL` | Coarse context-load size class per task. |
| P50/P80 estimates | Coarse ranges ("30–60 min") | Never fake precision (no "43 min"). |

`context amplification` — `unique files an agent must read / files it actually changes`.
The whole skill set is tuned to keep this ratio low.

## Replan actions (closed legal set)

`split`, `merge`, `reorder`, `change_dependency`, `defer`, `reduce_scope`,
`replace_route`, `checkpoint_and_split`, `request_contract_revision`.

**Append-only replanning** ("found a problem → add more tasks") is the forbidden
degenerate form; a legal replan may shrink or reshape work.

## Audit severity

- **BLOCKER** — plan must not be executed until fixed.
- **MAJOR** — should be fixed before execution; executor may surface it as risk.
- **MINOR** — fix if cheap; note in run manifest.

## Artifact index (one planning run)

```
<plan-dir>/
  repo-context-snapshot.json   repo-context-snapshot skill (stage 0)
  input.md                     raw user task (verbatim)
  stage-contract.json          stage-contract skill
  candidate-tasks.json         context-decomposer skill
  integration-plan.json        integration-planner skill
  dag.json                     dependency-dag skill
  risk-estimates.json          plan-risk-estimator skill
  tasks/<task-id>.json         task-packager skill (one per leaf, incl. integration tasks)
  audit.json                   plan-auditor skill (final verdict)
  run-manifest.json            orchestrator (pipeline + gate log)
  checkpoints/<task-id>.json   checkpoint-handoff skill (written during execution)
  replan-requests/*.json       replan-controller skill (interface reserved, V2)
```

Task ids: `T01`, `T02`, … (zero-padded). Contract ids: `C1`, `C2`, ….
Acceptance ids: `A1`, …. Seam ids: `S1`, ….
