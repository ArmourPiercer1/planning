---
name: integration-planner
description: Make integration explicit work. Identify every seam, create integration tasks (contract consistency check, seam integration with integration-only fix ownership, E2E closure gates including failure scenarios, final acceptance), and wire them into the DAG. Use as pipeline stage 4 of /long-task-planning, after dependency-dag. V1 is the minimal real implementation of this stage, with room to grow; never assume leaves integrate on their own.
---

# integration-planner

"Leaves done ⇒ system works" is a planning defect. This stage creates the
tasks that make closure explicit and owned. V1 scope is minimal but real; the
skill is the stable upgrade point. Vocabulary: `../../references/glossary.md`.

## Trigger

- Use: pipeline stage 4 (after `dag.json`); also any replan that adds/changes
  a seam.
- Do NOT use: to make leaves bigger (an integration task never absorbs leaf
  work); when the plan has a single leaf (nothing to integrate — say so).

## Inputs

- `stage-contract.json` (integration_seams, acceptance), `candidate-tasks.json`,
  `dag.json` (incl. `seam_bindings` — the concrete seam participants),
  `repo-context-snapshot.json` (for the new-wiring rule: which directories
  already contain code).

## Procedure

1. **Seam census.** Start from contract `integration_seams`; then add the
  implicit ones the contract missed: startup/lifecycle wiring, migrations,
  shared test fixtures, config/environment surfaces. Every seam gets the same
  `S…` id as the contract where possible.
2. **Consistency risk per seam.** For each seam, name what can silently
  diverge (field names, state values, error shapes, timing) — this becomes the
  E2E scenario list.
3. **Integration tasks** (assign the next free `T…` ids). Every one of the
   four kinds must be **satisfied exactly one way** — the semantics are
   `present / merged / omitted / missing`:
    - **present** — the kind is the primary `kind` of an integration task;
    - **merged** — a different task's `merged_kinds` lists it (small plans may
      merge `final_acceptance` into the `e2e_closure` task — set
      `merged_kinds: ["final_acceptance"]` on that task; never skip the kind
      silently);
    - **omitted** — an `omitted_kinds` entry with `kind`, `reason` (≥ 1
      sentence of justification) and `evidence` (≥ 1 concrete reference — a
      gate, a contract, a snapshot fact);
    - **missing** — none of the above. That is a planning defect
      (`INTEGRATION_KIND_MISSING`; BLOCKER for `seam_integration` when new
      wiring exists, MAJOR otherwise).
   The kinds:
    - `contract_consistency` — read-only diff of every implementation against
     the frozen specs (schemas, signatures, state machines); no behavior
      changes;
    - `seam_integration` — wires the seams; `owns_fixes_for` lists the leaves
     whose code it may patch for seam defects, and only those;
    - `e2e_closure` — runs the E2E gates; owns the e2e test paths;
    - `final_acceptance` — executes contract acceptance A… end to end and
      records evidence.
   **New-wiring rule (decides whether `seam_integration` may be omitted).**
   If any leaf creates a NEW file (absent from `repo-context-snapshot.json`)
   in a directory that already contains another leaf's existing code, new
   production wiring exists — the seam must be integrated by a task, and
   omitting `seam_integration` is `HIDDEN_INTEGRATION_WORK` (BLOCKER).
   Omitting is legitimate only when the Stage adds no wiring between existing
   components (new files land in fresh directories, or everything is consumed
   through already-existing registration points).
   Do not double-satisfy a kind: a kind that is both primary and merged, or
   merged and omitted, is `INVALID_INTEGRATION_MERGE` (MAJOR).
4. **E2E gates.** Each gate `E…` has a concrete scenario, the seams it covers,
   and evidence (test name/command). **Every seam needs ≥ 1 failure scenario**
   (crash/restart, retry exhaustion, not-found, bad input) — happy path alone
   is a hidden integration risk.
5. **DAG wiring.** For every integration task, add an edge from each covered
   leaf (`type: verification` or `data`) so it runs after them; fill
   `dag.json integration_gates` (gate id, task id, seams, acceptance ref).
   Update `parallel_groups` if a group now contains an integration task
   (it should be last).
6. Gate both artifacts with `plan-check.py validate`.

## Heuristics

- Integration tasks consume **upstream checkpoints + contracts + changed
  paths**, never the whole repo — they are the last context, not a re-read.
- Integration-only fix ownership is explicit or it does not exist: if a seam
  defect belongs inside a leaf, the integration task records the deviation and
  the leaf's checkpoint takes it — the integration task does not silently
  rewrite a leaf's owned module.
- One E2E gate per seam-cluster, not one per assertion; but never merge two
  seams with different consistency risks into one gate.
- If a seam cannot be gated deterministically (no observable difference), the
  seam definition is bad → BLOCKER back to `stage-contract`.

## Output

`<plan-dir>/integration-plan.json` (schema `planning/integration-plan@2` —
`integration_tasks[].kind` + optional `merged_kinds`, top-level optional
`omitted_kinds[]`) + amended `dag.json` (gates section + edges into
integration tasks).

## Failure & Escalation

- Seam without a deterministic gate → stop, escalate to `stage-contract`
  (the acceptance criteria or the seam is under-specified).
- An integration task would need to touch > 50% of a leaf's owned paths →
  the leaf boundary is wrong; escalate to `context-decomposer`.

## Examples

**Good.** Seams S1 (API↔worker via C2/C5), S2 (worker↔store via C5),
S3 (lifecycle↔worker via C4 startup hook). Tasks: T05 contract_consistency,
T06 seam_integration (owns_fixes_for [T01,T02,T03,T04]), T07 e2e_closure with
gates E1 submit→done (S1,S2), E2 crash-during-run→resume (S2,S3), E3 retry
exhaustion→failed (S2), E4 unknown id→404 (S1). Every gate names a pytest test.
Every kind is `present`; `omitted_kinds` is `[]`.

**Good (small plan, structured omission).** Two leaves, no new wiring
between existing components: T05 e2e_closure with
`merged_kinds: ["final_acceptance"]`, and
`omitted_kinds: [{kind: seam_integration, reason: "the seam wiring already
exists in the repo; this Stage adds no wiring between existing components",
evidence: ["S1"]}]` — no `HIDDEN_INTEGRATION_WORK` because no leaf creates
files next to another leaf's code.

**Anti-pattern.** No integration tasks — "the e2e tests in T03 will cover it";
one giant "final integration" task that owns every module's fix rights
(hides defects, kills local recoverability); or gates that only assert the
happy path.
