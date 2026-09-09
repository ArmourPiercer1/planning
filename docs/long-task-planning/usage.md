# Using the Long-Task Planning Skills

A practical guide for the two sides of the fence: the **planner** (running
the pipeline) and the **executor** (running one Task Package). Architecture
and reference material is in [README.md](README.md); the full executor
contract is in
`../../.agents/skills/long-task-planning/references/execution-protocol.md`.

## Planner side, step by step

1. **Invoke.**
   ```
   /long-task-planning <the task, or a file with it>
   ```
   The orchestrator creates a plan directory (convention:
   `plans/<slug>/`, or alongside the task input) and starts at stage 1.

2. **Stage 1 — freeze the scope (`stage-contract`).**
   Everything the later stages may not quietly change gets frozen here:
   objective, in/out-of-scope (with reasons — name the tempting refactors!),
   assumptions, architecture decisions, shared contracts `C*` with owners,
   integration seams `S*`, deterministic acceptance `A*` (each with
   positive/negative/failure cases and a named test), constraints, the
   time/compaction budget, and the `allowed_replan` set.
   Blocking open questions must be resolved *before* the freeze — an
   unresolved blocking question is a BLOCKER (`OPEN_BLOCKING_QUESTION`).
   Gate: `plan-check validate stage-contract.json`.

3. **Stage 2 — decompose by context closure (`context-decomposer`).**
   Ask "what must an agent *load* to do this, minimally?" — not "what
   feature is this?" Merge anything sharing a closure; split anything whose
   closure is >25 files or spans bare directories. Assign **disjoint
   `owned_paths`** (the parallelism guarantee). Gate: validate.

4. **Stage 3 — build the DAG (`dependency-dag`).**
   Enumerate edges by type (contract/data/ownership/verification). Then hunt
   fake serialization: if task A only needs task B's *spec* and that spec is
   a frozen contract, the edge is fake — remove it and record it in
   `fake_serialization_removed` with `why_not_real`. Compute the critical
   path (do not guess it) and emit parallel groups of disjoint owners.
   Gate: validate.

5. **Stage 4 — make integration explicit (`integration-planner`).**
   Census the seams (including implicit ones: who calls whom, who owns the
   fix when both sides are "done"). Create integration tasks — at minimum an
   `e2e_closure` and a `final_acceptance` (their absence is BLOCKER
   `NO_INTEGRATION_GATE`) — and give the seam-integration task
   `owns_fixes_for` over the leaves it may patch. Every seam needs at least
   one **failure-scenario** E2E gate (a happy-path-only gate set is exactly
   the defect the round-1 audit in the example caught). Amend `dag.json`
   gates. Gate: validate both files.

6. **Stage 5 — package (`task-packager`).**
   One self-contained `tasks/T*.json` per task: required context, inputs,
   frozen-contract refs, owned paths, non-goals, constraints, deliverables,
   acceptance tests with **evidence commands**, failure cases, integration
   dependency, handoff requirements. Test the package by the standard: a
   fresh agent that has seen *nothing else* must be able to start from it.
   Gate: validate each.

7. **Stage 6 — risk (`plan-risk-estimator`).**
   Score every task (S/M/L/XL rubric in the glossary; no point estimates —
   coarse P50/P80 ranges). Warnings must carry rationale; an oversized leaf
   needs `oversized_justification` or a split. The risk block inside each
   package is finalized here (stage 5 pre-fills, stage 6 owns). Gate:
   validate.

8. **Stage 7 — independent audit (`plan-auditor`).**
   Fresh subagent, artifacts + glossary only (never the planning
   conversation). Deterministic layer (`plan-check lint`) + the 13-check
   semantic list. Verdict is PASS iff zero BLOCKERs. On FAIL, the
   orchestrator applies the **targeted-revision map** — only the owning
   stage(s) of the findings re-run (e.g. `hidden_integration_work` →
   `integration-planner`; vague acceptance wording → `stage-contract`).
   Max 3 rounds; a 4th failure stops the pipeline and goes to the user with
   the audit trail.

9. **Hand off.** `audit.json` PASS + a clean `run-manifest.json` (full gate
   log) = the plan is executable. The orchestrator writes `HANDOFF.md`
   pointing at the plan directory.

### Running the deterministic checks yourself

```powershell
$env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"
uv run --no-project python .agents\scripts\plan-check.py lint plans\my-task
```

Exit codes: `0` clean · `1` findings ≥ threshold (default: BLOCKER) ·
`2` usage. Use `--fail-on MAJOR` for stricter local runs.

## Executor side, in one page

1. Read **only** `tasks/T0X.json` + the files in its `required_context`.
2. Implement against the frozen contracts. Expand context one file at a time
   *only* when blocked, and record every expansion as a `deviation`.
3. Classify what you discover:
   - **A — in-place**: fix it, stay inside your owned paths.
   - **B — backlog**: record it in the checkpoint (`newly_discovered_issues`,
     classification B, handling backlog). Do not fix it.
   - **C — blocker**: a frozen contract is wrong (`CONTRACT_CHANGE_REQUEST`)
     or a core seam is broken (`CORE_SEAM_BLOCKER`) → write the checkpoint
     with `status: blocked` and **stop**. Never patch another task's owned
     paths; never edit a frozen contract.
4. Checkpoint at stable subgoals: commit first, then
   `checkpoints/T0X.json` — concrete `verified_facts` (a downstream agent
   must not need to open your files), `changed_paths` inside your owned
   paths, test evidence, remaining DAG.
5. Stop immediately on any of the six unhealthy-run conditions (see the
   execution protocol): repeated identical failure, context bloat, ownership
   drift, compaction budget exceeded (≥4 per leaf), gate thrash, silent
   scope growth.

## Escalation paths (who decides what)

| Situation | Executor does | Planner/orchestrator does | User decides |
|---|---|---|---|
| A-class problem | fixes in place, notes in checkpoint | — | — |
| B-class discovery | records backlog in checkpoint | — | later triage |
| C-class `CONTRACT_CHANGE_REQUEST` | checkpoint `blocked`, stop | V1: stop + present request (no autonomous replan) | **yes** — contract revision is a scope decision |
| C-class `CORE_SEAM_BLOCKER` | checkpoint `blocked`, stop | routes to the owning integration task's fix path | if it fails 3 re-runs (gate_failure) |
| Unhealthy run | structured stop-report | `replan-request.json` (V1: write + stop) | **yes** — pick the action from the closed set |
| Audit FAIL round 1–3 | — | targeted revision (owning stages only) | — |
| Audit FAIL round 4 | — | stop with full audit trail | **yes** — accept, replan from stage 1, or abort |

The invariant in every row: **the executor never re-plans, the planner never
silently changes a frozen contract, and scope may only shrink.**

## FAQ

**Q: The task is too big even for this pipeline.**
Split into Stages first. Each Stage is a bounded unit whose Stage Contract
fits in one planning conversation. The Stage-N HANDOFF + checkpoints are the
input to Stage N+1. (Multi-stage chaining is V2 plumbing; in V1 you chain
them by hand.)

**Q: Audit failed three times. Now what?**
It stops — that is the rule, not a suggestion. Present the user with the
three `audit.json` rounds. Usually the pattern is one of: the scope is
wrong (re-run stage 1), a leaf is fundamentally oversized (re-run stage 2),
or the integration shape is wrong (re-run stage 4). The targeted-revision
map tells you which finding types own which stage.

**Q: A Task Package turns out to need a file not in `required_context`.**
That is a planning defect, not an executor one. The executor records the
expansion as a `deviation` and continues (one file at a time); after the
run, the deviation feeds back — if deviations are systematic, the
decomposer's closure was wrong and stage 2 re-runs.

**Q: Can the executor "just fix" the neighbor that's obviously wrong?**
No. Owned paths are the contract between parallel workers. The fix belongs
to the seam-integration task (`owns_fixes_for`) or to a replan. If the
neighbor is *blocking* you, that's an ordering defect: stop, report as a
blocker, let the planner add the edge.

**Q: Why no time estimates with real precision?**
P50/P80 coarse ranges only, by design. A fake-precise estimate ("47
minutes") is a planning smell — it invites the executor to defend the number
instead of the subgoal. The compaction budget (≥4 → re-split) is the real
size control.

**Q: Where do I see the whole thing working?**
`examples/long-task-planning/README.md` — a complete run including a real
round-1 audit FAIL and its targeted revision.
