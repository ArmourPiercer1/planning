---
name: context-decomposer
description: Build candidate leaf tasks by minimal context closure (files + contracts + concepts an agent must load), not by feature/module/directory. Estimates context footprint, flags cross-layer coupling, assigns disjoint owned paths. Use as pipeline stage 2 of /long-task-planning, after stage-contract. NOT for breaking work into to-dos — every output is a context-bounded closure, and NOT before the Stage Contract exists.
---

# context-decomposer

Decomposition boundaries = **the minimal context closure needed to complete the
work**, never the feature/module/directory outline. Output: candidate leaves for
the DAG stage. Vocabulary: `../../references/glossary.md`.

## Trigger

- Use: pipeline stage 2 (after `stage-contract.json` exists and is validated).
- Do NOT use: before the contract (you would decompose against unfrozen seams);
  for a task that is already one closure (don't manufacture tasks).

## Inputs

- `<plan-dir>/stage-contract.json` (frozen contracts, seams, acceptance, budget).
- Repo map of relevant territory: file → layer inventory. Gather with a **bounded**
  scan: directory listings, headers/signatures of key files. Do not read whole
  modules; the decomposer needs the map, not the content.

## Procedure

1. **Context inventory.** For the relevant territory, list files with their
   responsibility layer (`ui / store / api / service / runtime / persistence /
   lifecycle / e2e / tooling / docs`).
2. **Closures.** For each in-scope deliverable, list the actual closure:
   files that must be read, contracts that must be understood, concepts that
   must be mastered. Write it down — the closure list is the task boundary.
3. **Merge vs split.** Merge two work items only when *shared-context benefit >
   cross-layer coupling cost*: they share most of their closure, and combining
   does not cross a stable seam. Split when a closure crosses ≥ 3 responsibility
   layers or its file list approaches the broad-context threshold (25 files):
   find the stable seam inside it (interface, table, startup hook, test
   boundary) and cut there.
4. **Owned paths.** Assign each candidate disjoint `owned_paths`. Two
   candidates that must touch the same file → that is a real dependency or a
   bad boundary; resolve now (order them, or move the file to one owner).
   Integration tasks (later stage) own e2e test paths.
5. **Forbidden scope.** Per candidate: what it must NOT touch (other closures,
   other layers, listed non-goals).
6. **Split rationale.** One sentence per task: why this boundary is the
   closure (the auditor checks this).
7. Write `candidate-tasks.json`; gate with `plan-check.py validate`.

## Heuristics

- The **3-layer rule**: UI → service → runtime → persistence is not one leaf;
  check for a seam at each interface.
- Two small changes that both depend on the same complex state model →
  **merge** (splitting would make both agents re-learn the same model — pure
  context amplification).
- A leaf should be sized so its P50 is ~30–60 min of agent work; that is
  roughly: one closure, 1–3 contracts, ≤ ~15 files, ≤ 2 layers.
- Naming: name tasks by closure ("job store + schema"), never by feature
  ("the reports feature").
- If you cannot name the forbidden scope of a candidate, its boundary is fuzzy —
  redraw it.

## Output

`<plan-dir>/candidate-tasks.json` (schema `planning/candidate-tasks@1`).
Leaves only — integration tasks are created later by `integration-planner`.

## Failure & Escalation

- A closure crosses 3+ layers and **no** stable seam exists → mark it XL in the
  split rationale and flag it; the risk stage will demand a keep-single-leaf
  justification or a different boundary. Do not silently ship an unbounded leaf.
- Two in-scope deliverables share files so heavily that no disjoint owned paths
  exist → escalate: the Stage boundary or the contract is wrong; go back to
  `stage-contract`.
- Repo territory too unknown to inventory → stop and say which areas need a
  deeper read (a bounded pre-read task is a legitimate replan).

## Examples

**Good.** "Report generation" becomes 4 closures: (T01) persistence — owns the
model + job store module + migration + its unit tests, reads only the DB-fixture
file and contract C1/C5; (T02) runtime — owns the worker module + tests, reads
the state-machine contract C3 and a *fake* of C5 (frozen, so it never needs the
real store); (T03) API — owns the route module, reads C2 + an existing router as
pattern; (T04) lifecycle — owns lifespan wiring + recovery module, reads C3/C4/C5
+ `main.py`. Disjoint owned paths; each forbidden_scope names the others' files.

**Anti-pattern.** One task "implement report generation" spanning
`app/api/`, `app/services/`, `app/db/`, `app/main.py` (7 layers, no closure); or
one task per module that forces three agents to re-read the same state model
(over-fragmentation — merge rule violated in the other direction).
