---
name: stage-contract
description: Compile a bounded user task into a frozen Stage Contract (objective, in/out-of-scope, frozen assumptions and architecture decisions, shared contracts, integration seams, deterministic acceptance, constraints, budget, allowed replan actions). Use as pipeline stage 1 of /long-task-planning, or standalone when a long task needs its scope and shared seams frozen before execution. NOT a design doc, and NOT for small single-session tasks., horizon awareness (commitment/detailed/forecast), stage boundary selection, and next-planning-trigger definition
---

# stage-contract

Freeze the **minimal** shared agreement that unlocks parallel execution —
before any implementation task. The contract is deliberately not "the complete
overall design": only what crosses task boundaries gets frozen now.
Vocabulary: `../../references/glossary.md`.

## Trigger

- Use: pipeline stage 1; user asks to "freeze scope / non-goals / contracts" for
  a long task; a previous Stage failed from scope drift or reopened decisions.
- Do NOT use: for tasks with no parallelism and no shared seams (contract-first
  buys nothing); as a substitute for a design document the user actually wants.

## Inputs

- `<plan-dir>/input.md` (verbatim user task) — create it first if missing.
- `<plan-dir>/repo-context-snapshot.json` (stage 0 output) — the bounded repo
  scan: file/layer map, one-hop imports, known TODOs/tech debt, shared files.
  It replaces an ad-hoc "repo notes" scan: read the snapshot, and spot-check
  only files it lists. If it is missing, run stage 0 first — the contract's
  seam and non-goal claims are only as good as the repo picture behind them.
- User constraints and budget.

## Procedure

1. **Objective + in-scope.** One-sentence objective; list in-scope items as
   concrete deliverables, not activities.
2. **Out-of-scope with reasons.** Every item needs a `reason`. Include the
   temptations you found in the repo (TODOs, ugly code, unrelated refactors) —
   a non-goal you didn't see is a scope-creep hole.
3. **Shared contracts first (the heart of this stage).** List every interface
   that ≥ 2 tasks will touch (API, schema, state machine, service interface,
   data format). For each: `id` (C1…), `kind`, a spec precise enough that two
   agents cannot interpret it differently, `logical_owner` (the
   responsibility/layer that implements it — e.g. `persistence`, `api`,
   `runtime`, or `planner (from user requirement)`; **never a task id — task
   ids do not exist yet**, the DAG stage binds this to a concrete task),
   `frozen: true` for the ones that must unlock parallel work. **Freeze the
   seams that unlock parallelism now**; defer the rest — do not wait for a full
   design.
4. **Frozen assumptions** (A-…): each with statement + rationale + what would
   invalidate it.
5. **Frozen architecture decisions** (DA-…): structural choices only
   (worker model, storage, process boundaries), each with rationale + seams
   affected.
6. **Integration seams** (S…): the exact meeting points, with the contract ids
   they carry and `participants` as LOGICAL roles/components (e.g.
   `api`, `runtime`, `persistence`, `lifecycle`) — never task ids; the DAG
   stage binds each participant role to a concrete task.
7. **Deterministic acceptance** (A1…): observable behavior, each with
   `positive_case`, `negative_case`, `failure_behavior`, and `evidence`
   (a test name, command, or concrete observable — "returns 404 with field X",
   never "works correctly").
7a. **Delivery profile.** Set `delivery_profile.level` to one of:
    `prototype` (proof of concept), `alpha` (core feature works, focused tests),
    `beta` (feature complete, missing polish/edge cases), `rc` (release
    candidate, migration + compatibility verified), `production` (full assurance).
    Default to `alpha` if the user doesn't specify. The delivery profile gates
    what the auditor considers blocking.
7b. **Planning budget.** If the task is large or the user has a cost constraint,
    set `planning_budget` with sensible defaults:
    ```json
    "planning_budget": {
      "max_full_audits": 2,
      "max_plan_revisions": 3,
      "max_planning_subagents": 5,
      "soft_wall_fraction": 0.3
    }
    ```
    `soft_wall_fraction` = fraction of total budget that, if consumed by
    planning alone, triggers a warning.
8. **Constraints + resource budget.** Coarse targets: leaf P50/P80 ranges,
   max compactions per leaf, stage estimate in dev-time (ranges, not fake
   precision).
9. **allowed_replan** — pick from the closed legal set
   (`split, merge, reorder, change_dependency, defer, reduce_scope,
   replace_route, checkpoint_and_split, request_contract_revision`).
10. **Open questions.** Blocking ones must be resolved (ask the user, in one
    batch) **before** the contract is considered frozen; non-blocking ones are
    recorded with owner.
11. Gate: `uv run --no-project python ../../scripts/plan-check.py validate <plan-dir>/stage-contract.json`
    (set `UV_CACHE_DIR` to a writable path if the sandbox denies the default).
    Non-zero exit → fix, do not proceed.
12. **Horizons** (three-level output). Classify every planned task into one
    horizon:
    - `commitment` — tasks whose route is certain and will execute regardless
      of what evidence comes in; these have full Task Packages
    - `detailed_stage` — tasks whose route is the current best plan but depends
      on assumptions being validated; these have full Task Packages
    - `forecast` — future stages whose route depends on evidence not yet
      available; these get stage-level objective + depends_on_evidence, NO
      detailed DAG, NO Task Packages
    Write the classification into `stage-contract.json` `horizons` field.
13. **Stage boundary.** Explain why this stage ends where it does. The stage
    should end at one or more of:
    - new evidence that could change subsequent route
    - high-risk assumption being validated
    - shared seam being stabilized and frozen
    - independently verifiable capability increment
    - context cluster for next stage clearly differs
    - budget envelope boundary
    Write `stage_boundary` into `stage-contract.json`.
14. **Next planning trigger.** Define what triggers the next planning point:
    ```json
    "next_planning_trigger": {
      "normal": ["stage_acceptance_reached"],
      "early": [
        "frozen_assumption_falsified",
        "core_seam_blocker",
        "route_changing_evidence",
        "budget_envelope_threatened"
      ],
      "not_triggers": [
        "first_worker_failure",
        "optional_bug",
        "mechanical_merge_conflict"
      ]
    }
    ```

## Heuristics

- **No task ids, ever.** `logical_owner` and seam `participants` name
  responsibilities/roles. Writing `T01` here front-loads a decomposition
  decision and breaks when the DAG rebinds; plan-check rejects it as
  `CONTRACT_OWNER_TASK_ID` / `SEAM_PARTICIPANT_TASK_ID`.
- **Minimal contract**: if a spec only one task consumes, it belongs in that
  task's package, not in the contract.
- **Acceptance is written test-first**: naming the test that will prove it
  (`tests/e2e/test_x.py::test_y`) catches vagueness early.
- Every "maybe later" goes to `out_of_scope` with reason — deferral is a
  decision, not an accident.
- Task boundary unclear → ask the user (one batched question set), do not guess;
  an unguessable boundary is an `open_question` with `blocking: true`.
- Scope > ~2 dev-days → stop and propose a Stage split instead of a bloated
  contract.

## Output

`<plan-dir>/stage-contract.json` (schema `planning/stage-contract@3`).
The new @3 schema adds: `delivery_profile`, `planning_budget`, `horizons`,
`stage_boundary`, `next_planning_trigger`. All are optional for backward
compatibility with existing plans.
Single writer: this skill only. The contract never references task ids —
ownership is logical (`logical_owner`, role participants); concrete binding
happens in the DAG stage, so rebinding a contract never rewrites this artifact.

## Failure & Escalation

- Blocking open question unresolved after asking the user → stop; do not
  fabricate a resolution.
- User's task is actually two Stages → stop with a split proposal.
- Gate fails → fix the artifact in place; repeated failure means the inputs
  (input.md/repo notes) are insufficient — report back.

## Examples

**Good.** `shared_contracts` includes `C2 (api): POST /reports → 202 {job_id};
GET /reports/{id} → 200 {status, attempts, progress, result_ref|error}, 404 for
unknown id` with `frozen: true`, so the API task and the worker task can run in
parallel against the same frozen spec. `out_of_scope` explicitly lists the
legacy CSV-export refactor found in the repo, with reason "does not touch report
jobs; tracked separately".

**Anti-pattern.** Waiting to freeze the API until the full worker design is
done (late contract freeze — kills parallelism); acceptance reading
"job processing works correctly and is sufficiently tested" (nondeterministic —
no third party could judge PASS/FAIL).
