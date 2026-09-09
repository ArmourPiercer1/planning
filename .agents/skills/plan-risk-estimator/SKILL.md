---
name: plan-risk-estimator
description: Attach structured, explainable risk estimates to every task — context footprint S/M/L/XL, touched layers, cross-contract count, statefulness, integration distance, uncertainty, coarse P50/P80 ranges, compaction risk, warnings with rationale — and force an oversized-leaf justification. Heuristic V1, deliberately no fake time precision. Use as pipeline stage 6 of /long-task-planning; owns the risk blocks inside Task Packages.
---

# plan-risk-estimator

Context and tokens are **planning resources**, not afterthoughts. This stage
scores each task so the auditor (and future replans) can see which leaves are
likely to run away — with a rationale for every number. Vocabulary:
`../../references/glossary.md`.

## Trigger

- Use: pipeline stage 6 (packages exist).
- Do NOT use: to produce false precision ("43 minutes"); to gate the plan
  (that is the auditor's job).

## Inputs

- `candidate-tasks.json`, `integration-plan.json`, `dag.json`,
  `stage-contract.json` (budget targets), `tasks/*.json`.

## Procedure

For each task (leaves + integration tasks):

1. **Context footprint** (documented rubric):
   - `S` — ≤ 8 context files, ≤ 2 layers, ≤ 2 contracts;
   - `M` — ≤ 20 files, ≤ 3 layers, ≤ 3 contracts;
   - `L` — ≤ 40 files, ≤ 4 layers, or 4 contracts;
   - `XL` — beyond that, or crosses a stable seam that should have split it.
2. **Touched layers, cross_contracts** — from the package, copied, not
   re-derived.
3. **Statefulness** — `low` (pure function-ish, no persisted state),
   `medium` (reads/writes one store), `high` (concurrency, retries,
   cross-process state, lifecycle).
4. **Integration distance** — graph hops from this task to the nearest
   integration gate: `low` = 0–1, `medium` = 2, `high` = 3+ (long tails
   between leaf completion and verified closure).
5. **Uncertainty** — `low` (well-known territory, contracts precise),
   `medium` (some unknowns in repo territory), `high` (new tech, unclear
   existing behavior, under-specified contract).
6. **P50 / P80** — coarse ranges from the rubric baseline (S ≈ 30–60 min P50;
   scale by footprint × statefulness × uncertainty). Always a **range**;
   never a point estimate. Compare against the Stage budget; exceeding
   `leaf_p80_max` is a warning, not a gate. If P80 exceeds target, record
   it — but do not demand a revision. The governor handles the schedule-fit
   decision.
7. **Compaction risk** — from footprint + statefulness + uncertainty:
   `high` when ≥ 4 compactions are plausibly expected (footprint L/XL with
   statefulness ≥ medium or uncertainty high).
8. **Warnings** — every warning is `{code, detail, rationale}`:
   - `SPLIT_RECHECK_REQUIRED` — compaction risk high or p80 > budget: mandatory
     re-split check;
   - `OVERSIZED_LEAF` — footprint XL: `oversized_justification` **required**
     (why one leaf: shared closure, no stable seam, cost of re-reading);
   - `LONG_INTEGRATION_TAIL` — integration distance high;
   - `UNCERTAINTY_DOMINANT` — uncertainty high with footprint ≥ M;
   - `CONTRACT_DENSITY` — ≥ 4 cross-contracts (each is a re-read point).
9. Write `risk-estimates.json`; copy the final risk blocks into
   `tasks/*.json` (this stage owns those blocks — stage 5 only prefilled).
10. Gate: `plan-check.py validate` (both artifact and every amended package).

## Heuristics

- A warning without a rationale is a guess — the auditor rejects unexplained
  warnings.
- Two adjacent S tasks that share one complex state model are cheaper merged
  than split (flag if the plan shows such fragmentation with a
  `FRAGMENTATION_CANDIDATE` warning, rationale: shared-context benefit).
- Integration tasks are expected to be the highest integration-distance-0
  nodes; if a *leaf* has distance high while small, the DAG tail is the
  problem, not the leaf.
- Estimating is not forecasting: if the repo territory is too unknown to
  classify, set uncertainty high + a warning and say which fact would settle
  it (a bounded pre-read is a legitimate replan trigger).

## Output

`<plan-dir>/risk-estimates.json` (schema `planning/risk-estimates@1`) + final
`risk` blocks in all `tasks/*.json`.

## Failure & Escalation

- Any XL without `oversized_justification` → invalid artifact; either justify
  or split (back to `context-decomposer`).
- Budget blown by the plan as a whole (sum of p80s ≫ Stage estimate with
  little parallelism) → warning in the summary. The auditor records it but
  does NOT force a replan. Schedule is a forecast: the governor decides
  whether to proceed, cut scope (at most one pass), or escalate to the user.
  Never force the planner to keep revising until the numbers look good — that
  is the runaway this version fixes.

## Examples

**Good (excerpt, T02).**
`{context_footprint: M, touched_layers: [service, runtime], cross_contracts: 3,
statefulness: high, integration_distance: medium, uncertainty: low,
p50: "45-75 min", p80: "90-120 min", compaction_risk: medium,
warnings: [{code: CONTRACT_DENSITY, detail: "consumes C3+C4+C5",
rationale: "each contract is a re-read point; kept one leaf because all three
specify the same state machine — splitting would force re-reading all three in
two agents"}, {code: SPLIT_RECHECK_REQUIRED, detail: "p80 may exceed budget",
rationale: "concurrency + retry logic; if execution exceeds p80, checkpoint_and_split
around the retry policy"}], oversized_justification: null}`

**Anti-pattern.** Every task `p50: "42 min"`, no warnings, XL leaf with
`oversized_justification: "fine"` — unexplained estimates are the planning
equivalent of a missing test.
