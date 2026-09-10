---
name: dependency-dag
description: Compile candidate leaf tasks into an execution DAG with typed edges (contract, data, ownership, verification), detect fake serialization and ownership collisions, extract the critical path, and emit parallel groups. Optimizes for short critical path and few integration conflicts, not maximum concurrency. Use as pipeline stage 3 of /long-task-planning, after context-decomposer. NOT for ordering prose steps, and NOT before candidate tasks exist.
---

# dependency-dag

The DAG encodes **real semantic dependencies**. Markdown section order,
requirements-doc order, or "the backend was written first" are never edges.
Vocabulary: `../../references/glossary.md`.

## Trigger

- Use: pipeline stage 3 (`candidate-tasks.json` + `stage-contract.json` exist).
- Do NOT use: to serialize work that has no real dependency (that is the
  failure mode); before decomposition.

## Inputs

- `<plan-dir>/candidate-tasks.json`
- `<plan-dir>/stage-contract.json` (frozen contracts + LOGICAL owners, seam
  participants by role, unlock assumptions)
- `<plan-dir>/repo-context-snapshot.json` (context for the ownership/binding
  decisions: which component actually implements each contract)

## Procedure

1. **Edge census.** For every ordered pair (A, B) ask: what does B actually
   consume from A? Classify into exactly one type:
   - `contract` — B reads a contract that A owns/finalizes (and the contract is
     not frozen for parallel unlock);
   - `data` — B consumes concrete output of A (files, tables, binaries, fixtures);
   - `ownership` — A and B touch the same path, so they must be ordered;
   - `verification` — B exists to verify A (gates, integration).
   No defensible type → **no edge**. Every edge gets a one-sentence `reason`.
2. **Fake serialization.** For each pair that a naive reading would order
   (doc order, naming), record it in `notes.fake_serialization_removed` with
   `why_not_real`. If you find none, say so explicitly (empty list + note) —
   the absence is a claim the auditor checks.
3. **Parallel groups.** Group tasks with no unsatisfied path between them.
   Hard constraint: disjoint owned paths inside a group (check prefix overlap —
   `app/db/` vs `app/db/models.py` is an overlap).
4. **Unlock contracts.** For each frozen contract that lets ≥ 2 tasks run
   before their owner finishes, add `unlock_contracts` entry
   (contract_id, unlocks). If a parallel group consumes a non-frozen contract
   of an unfinished owner, add the ordering edge instead.
5. **Bind the logical owners (new in @2).** The stage contract names only
   LOGICAL owners and role participants — task ids do not exist yet. Now that
   the leaves exist, write:
   - `contract_bindings`: one entry per shared contract — `contract_id`,
     `owner_task` (the leaf whose owned paths implement/finalize the contract;
     use the snapshot's layer map to see which component that is),
     `consumer_tasks` (the tasks that consume it), `rationale`.
   - `seam_bindings`: one entry per integration seam — `seam_id`,
     `participant_tasks` (≥ 2 distinct leaves, one per participant role),
     `rationale`.
   Every contract and every seam must be bound — an unbound contract has no
   concrete owner and the plan is incomplete (`UNBOUND_CONTRACT` /
   `UNBOUND_SEAM`, BLOCKER). Rebinding later = editing `dag.json` only; the
   stage contract is never rewritten for a binding change.
6. **Critical path.** Compute the longest chain (unit weights) and set
   `critical_path` to it. If your declared path is shorter than the computed
   longest, your DAG or your path is wrong — fix the DAG, not the label.
7. Integration task slots: `integration_gates` stays empty for now;
   `integration-planner` (stage 4) assigns integration task ids, adds the
   edges into them, and fills the gates. Do not invent integration tasks here.
8. Write `dag.json`; gate with `plan-check.py validate`.

## Heuristics

- **Minimize critical-path length and integration conflict; do not maximize
  concurrency.** A 2-task group that forces a third task to wait is worse than
  3 smaller groups with one shared file ordered.
- Contract freeze is a parallelism tool: if two tasks would serialize only
  because both read C3, freeze C3 (or check it is already frozen) instead of
  adding an edge.
- An edge with `reason: "needed for testing"` is usually a `data` dependency on
  a test double that a frozen contract can delete — prefer the fake.
- If every pair ends up ordered, you have serialized by fear: re-examine each
  edge's type.

## Output

`<plan-dir>/dag.json` (schema `planning/dag@2`), leaves only plus empty
integration-gate slot, plus the `contract_bindings` / `seam_bindings` that
make every logical owner and seam participant concrete. Amended later by
`integration-planner` (single-writer per section: leaves + bindings by this
skill, gates by integration-planner).

## Failure & Escalation

- Cycle discovered → the "dependency" is mis-typed or the boundary is wrong;
  go back to `context-decomposer` rather than breaking the cycle arbitrarily.
- Two leaves cannot get disjoint owned paths and have no real ordering either →
  boundary defect; escalate to `context-decomposer`.
- Critical path > 40% of total tasks in a chain with ≥ 3 tasks → flag in
  `notes.free_parallelism_trades`; the risk/audit stages will look at it.

## Examples

**Good.** Requirements list store → worker → API → recovery in that order, but
the only real edges are T01→T04 (recovery queries the real table) and
T01/T02/T03/T04→T05 (integration verification). T02 and T03 run against frozen
contracts C3/C5 with test fakes; the doc-order pair (API before recovery) is
recorded in `fake_serialization_removed` with `why_not_real: "API never calls
recovery; both only consume frozen contracts"`. `contract_bindings` maps
C1/C5 (logical owner `persistence`) to T01 and C4 (logical owner `runtime`)
to T02 — the stage contract itself still says `persistence`, not `T01`.

**Anti-pattern.** Edges for every doc-order pair ("T02 depends on T01 because
the design doc mentions the store first"), no reasons, critical path = all
tasks, and a comment "we can parallelize later" — fake serialization with a
label on it.
