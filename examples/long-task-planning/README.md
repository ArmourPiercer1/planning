# End-to-end example — `report-jobs-v1`

A complete, hand-authored planning run for a realistic long task:
**"Add resumable long-running report generation to a FastAPI service"**
(full user task in [`input.md`](input.md)). Every artifact below was produced
by following the skills in
[`../../../.agents/skills/`](../../../.agents/skills/) and passing every
`plan-check` gate. This example is also the fixture the test suite re-validates.

## What this example demonstrates

| Failure mode (bootstrap doc §1) | Where it is handled here |
|---|---|
| Scope creep | `input.md` teases a legacy-CSV refactor; the contract names it in `out_of_scope` with a reason; audit F03 (round 2) records it as a positive control |
| Re-reading the repo per task | Decomposition by context closure (T01–T04 each have ≤ 5 context files); T02/T03 run **parallel** against frozen contracts + test fakes |
| Reopening frozen decisions | C1–C6 frozen in stage 1; T06's package says a contract-level defect is a `CONTRACT_CHANGE_REQUEST`, not a fix |
| Unclear dependencies / fake serialization | 3 doc-order pairs recorded in `dag.json notes.fake_serialization_removed` with `why_not_real` |
| Leaves done but integration not closed | T05–T08 exist as explicit tasks; round-1 audit **FAILED** because E2E failure scenarios (crash recovery, retry exhaustion) were missing — then fixed by a targeted revision |
| Oversized leaves | T06 spans 4 layers by design — the risk stage pre-commits a `checkpoint_and_split` per seam; audit F02 (round 2) notes it MINOR |
| Blocker handling | T01 checkpoint shows B-class discovery (backlog); T06/T07 packages define the C-class paths |
| Local recoverability | Each leaf checkpoints at stable subgoals; a failed leaf invalidates only its downstream subgraph |

## Artifact map

```
input.md                     raw user task (verbatim, incl. the scope-creep tease)
stage-contract.json          6 frozen contracts, 3 seams, 6 deterministic acceptance items
candidate-tasks.json         4 leaves by context closure (T01 store, T02 worker, T03 API, T04 lifecycle)
integration-plan.json        seams S1-S3 + integration tasks T05-T08 + E2E gates E1-E4
dag.json                     13 typed edges, 6 parallel groups, critical path T01→T04→T05→T06→T07→T08
risk-estimates.json          S/M/L footprint + warnings with rationale per task
tasks/T01..T08.json          self-contained Task Packages (executor reads only these)
audit-v1.json                round-1 audit: FAIL (BLOCKER hidden_integration_work + 2 findings)
audit.json                   round-2 audit: PASS (3 MINOR findings carried as warnings)
run-manifest.json            full pipeline + gate log incl. the targeted-revision round
checkpoints/T01.json         example execution checkpoint (context handoff artifact)
```

## The revision loop, shown for real

Round 1 (fresh isolated subagent) found a **BLOCKER**: the integration plan
only gated the happy path — crash recovery (A3) and retry exhaustion (A4), the
two riskiest behaviors of the Stage, had no E2E gate. Per the orchestrator's
targeted-revision map, only `integration-planner` (add E2/E3) and
`stage-contract` (fix A6's vague wording, name the legacy non-goal) were
re-run. Round 2: PASS. See `run-manifest.json` pipeline/gates for the full log.

## How to re-verify this example

```powershell
$env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"   # sandbox-friendly uv cache
uv run --no-project python ..\..\..\.agents\scripts\plan-check.py lint  .
uv run --no-project python ..\..\..\.agents\scripts\plan-check.py report .
```

`lint` exits 0 with zero findings on this directory. The test suite
(`tests/planning-skills/`) re-validates every artifact against the shared
schemas automatically.

## How an execution agent consumes this plan

1. Read **only** `tasks/T01.json` (its package) and the files listed in its
   `required_context`.
2. Implement; classify every discovered problem A/B/C (see
   `long-task-planning/references/execution-protocol.md`).
3. At each stable subgoal, write `checkpoints/T01.json` (see the example
   checkpoint in this directory).
4. The executor never reads the other artifacts — that is the point.
   Integration tasks (T05–T08) consume upstream **checkpoints**, not the repo.
