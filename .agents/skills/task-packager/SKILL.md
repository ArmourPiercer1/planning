---
name: task-packager
description: Compile every leaf (and integration task) into a self-contained Task Package that a fresh execution agent can start from without reading any other plan artifact — required context, inputs, frozen contracts, owned paths, non-goals, constraints, deliverables, deterministic acceptance tests, failure cases, integration dependency, handoff/checkpoint requirements. Use as pipeline stage 5 of /long-task-planning. The package's risk block is filled later by plan-risk-estimator (stage 6).
---

# task-packager

One file per task, and that file must be **sufficient**. The executor reads the
package + `required_context` and starts; if the package needs "see the rest of
the plan" it is not a package, it is a pointer. Vocabulary:
`../../references/glossary.md`.

## Trigger

- Use: pipeline stage 5 (contract, candidates, DAG, integration plan exist).
- Do NOT use: to re-decide boundaries or dependencies (owning stages are 2–4);
  for tasks without frozen acceptance (fix the contract first).

## Inputs

- `stage-contract.json`, `candidate-tasks.json`, `integration-plan.json`,
  `dag.json`.

## Procedure

For **each** task id (candidate leaves + integration tasks), write
`tasks/<id>.json`:

1. `objective` — executable sentence with an observable outcome (the auditor
   rejects bare "implement X").
2. `required_context` — the closure: files (exact paths, no bare top-level
   directories), contract ids, concepts. This is the *only* context the agent
   may load at startup.
3. `inputs` — concrete inputs (upstream outputs, fixtures, data).
4. `frozen_contracts` — for each consumed contract, `contract_id` +
   `spec_ref` pointing at its spec in `stage-contract.json`. The executor
   treats these as read-only.
5. `owned_paths` — from the candidate; integration tasks own their test paths.
6. `allowed_dependencies` — upstream tasks whose *outputs* (not code-reading
   beyond outputs) this task may consume, with `what`.
7. `non_goals` — task-specific prohibitions + inherited Stage non-goals that
   are plausible temptations here.
8. `implementation_constraints` — technical rules (no new deps, test style,
   error handling pattern, files not to touch beyond owned paths).
9. `deliverables` — what/where pairs (code paths, test paths, docs).
10. `acceptance_tests` — deterministic tests, named now (test file::test name
    may not exist yet — naming it is the commitment), each with
    `case: positive|negative|failure`, observable description, and `evidence`
    (command + expected outcome). Mirror the contract's acceptance items that
    this task contributes to.
11. `failure_cases` — scenarios the implementation must handle with defined
    behavior.
12. `integration_dependency` — seams this task participates in, upstream
    outputs it needs, consumers of its outputs.
13. `handoff` — `checkpoint_required: true` always,
    `checkpoint_ref: checkpoints/<id>.json`, downstream consumers, and notes
    the next agent must see.
14. `risk` — **placeholder filled by `plan-risk-estimator` (stage 6)**; the
    schema requires the full block, so write the block with the estimator's
    output verbatim when stage 6 runs. (Stage 5 may prefill estimates, stage 6
    owns the final values.)
15. Gate: `plan-check.py validate` on every package file.

## Heuristics

- **Self-contained test**: read only the package (pretend you have never seen
  the plan). If you cannot start the task, add what is missing — that is the
  acceptance criterion for the package.
- `required_context` minimalism is enforced by lint (> 25 files or a bare
  directory → finding). If a task truly needs that much, the boundary is wrong
  → back to `context-decomposer`.
- Acceptance tests are the contract between planner and executor; vague
  wording here is the #1 nondeterministic-acceptance source the auditor hunts.
- A package that says "also keep an eye on X" is leaking scope into the
  executor's judgment — convert it to a non_goal or a separate issue record.

## Output

`<plan-dir>/tasks/<id>.json` per task (schema `planning/task-package@1`),
risk blocks finalized by stage 6.

## Failure & Escalation

- A field cannot be filled with real evidence (no deterministic acceptance
  exists for this task) → do not invent it; stop and mark a finding for
  `stage-contract` (the acceptance is missing) — this is a BLOCKER-shaped
  defect at audit time.
- Two packages end up claiming the same file → ownership collision; back to
  `dependency-dag`/`context-decomposer`.

## Examples

**Good (excerpt, T02 runtime worker).**
`required_context.files` = [`app/services/report_worker.py` (new),
`app/services/report_gen.py` (existing interface, read-only),
`tests/services/test_report_worker.py` (new)]; `frozen_contracts` =
[C3 state machine, C5 job store interface]; `acceptance_tests` include
`{case: failure, description: "generator raises on attempt 3 of 3, job row
writes status 'failed', attempts 3, error message, no 4th attempt",
evidence: "pytest tests/services/test_report_worker.py::test_retry_exhaustion
→ passed; row assertions in test"}`; `handoff.checkpoint_required: true`.

**Anti-pattern.** Objective "implement the report worker";
`required_context.files: ["app/"]`; no non_goals; acceptance "worker works
correctly under all conditions"; handoff notes "see plan for details".
