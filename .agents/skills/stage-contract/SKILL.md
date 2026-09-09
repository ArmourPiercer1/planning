---
name: stage-contract
description: Compile a bounded user task into a frozen Stage Contract (objective, in/out-of-scope, frozen assumptions and architecture decisions, shared contracts, integration seams, deterministic acceptance, constraints, budget, allowed replan actions). Use as pipeline stage 1 of /long-task-planning, or standalone when a long task needs its scope and shared seams frozen before execution. NOT a design doc, and NOT for small single-session tasks.
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
- Repo notes: layer map of relevant directories, known tech debt/TODOs
  (bounded scan only).
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
   agents cannot interpret it differently, `owned_by` (task id or "user-provided"),
   `frozen: true` for the ones that must unlock parallel work. **Freeze the
   seams that unlock parallelism now**; defer the rest — do not wait for a full
   design.
4. **Frozen assumptions** (A-…): each with statement + rationale + what would
   invalidate it.
5. **Frozen architecture decisions** (DA-…): structural choices only
   (worker model, storage, process boundaries), each with rationale + seams
   affected.
6. **Integration seams** (S…): the exact meeting points, with participants and
   the contract ids they carry.
7. **Deterministic acceptance** (A1…): observable behavior, each with
   `positive_case`, `negative_case`, `failure_behavior`, and `evidence`
   (a test name, command, or concrete observable — "returns 404 with field X",
   never "works correctly").
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

## Heuristics

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

`<plan-dir>/stage-contract.json` (schema `planning/stage-contract@1`).
Single writer: this skill only.

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
