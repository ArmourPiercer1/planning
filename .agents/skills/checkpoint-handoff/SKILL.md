---
name: checkpoint-handoff
description: Execution-time skill that turns a completed (or stopped) stable subgoal into a machine-readable checkpoint — the context handoff artifact carrying revision, contracts satisfied, changed paths, test evidence, verified facts, deviations, newly discovered issues classified A/B/C, blockers of kind CONTRACT_CHANGE_REQUEST or CORE_SEAM_BLOCKER, remaining DAG, and downstream notes, drift tracking against project contract, verified/falsified assumptions, and recursive plannability checks. Use during execution of any Task Package, at each stable subgoal, on blocker, and on unhealthy-run stop. NOT a planning stage and NOT a git commit message.
---

# checkpoint-handoff

A checkpoint is **how the next agent avoids re-reading your work**. If the
downstream agent still has to open your changed files to know what is true,
the checkpoint failed its job. Vocabulary: `../../references/glossary.md`.

## Two levels — do not confuse them

| | `planning/checkpoint@2` (this skill) | `planning/stage-checkpoint@1` (stage completion) |
|---|---|---|
| Granularity | one per task / stable subgoal | one per stage |
| Written by | the executing agent, as it goes | the orchestrator at stage end, from the task checkpoints |
| Consumer | the next task's executor | the **next stage's planner** |
| Content | revision, contracts satisfied, changed paths, tests, verified facts, deviations, issues, blockers, remaining DAG | compressed: completed tasks, contracts satisfied, verified/falsified assumptions, scope drift, acceptance status, next-stage inputs, stop reason |
| NOT | a stage-completion artifact | a replacement for task checkpoints |

`checkpoint@2` is **task-level**. It is not, by itself, evidence that a
stage is complete. Stage completion is the stage-checkpoint: at the end of
the stage (after the last task checkpoint exists and the stage acceptance
gate passes), the orchestrator writes `<plan-dir>/stage-checkpoint.json`
(schema `planning/stage-checkpoint@1`) — a thin compression of everything the
**next stage's planner** must know, so the next stage never has to re-read
every task checkpoint to start. Required content is defined by the schema:
`completed_tasks`, `satisfied_contracts`, `falsified_assumptions`,
`scope_drift`, `acceptance_status` (met/unmet/deferred),
`next_stage_inputs`, `stop_reason`, `downstream_notes`.

The recursive-plannability checks below gate the stage-checkpoint: if any
answer is "no", the stage-checkpoint is written with `status: "blocked"` (or
`replan_required`) instead of `complete`, and the next stage does not start
on top of it.

## Trigger

- Use: (a) at every **stable subgoal** inside a task (a point where another
  agent could continue from the checkpoint alone); (b) at task completion;
  (c) on blocker; (d) on unhealthy-run stop (see execution protocol).
- Do NOT use: after every edit (noise); as a substitute for commits (write the
  commit first, the checkpoint records it).

## Inputs

- The Task Package being executed; the current work state; the repo revision.

## Procedure

1. **Commit** the current work (clean boundary); capture `revision`
   (sha, branch, timestamp).
2. Fill `checkpoints/<task-id>.json` (schema `planning/checkpoint@2`):
   - `status` — `complete` / `partial` / `blocked`;
   - `completed` — what is done, one paragraph max;
   - `contracts_satisfied` — contract ids whose spec this task verified
     against reality (the integration task's main input);
   - `changed_paths` — everything changed. Must stay inside `owned_paths` +
     this task's test paths; anything else is a scope violation → record it in
     `deviations` with the reason (self-flag, don't hide);
   - `tests` — passed/failed test ids + the evidence command(s) that ran them;
   - `verified_facts` — concrete facts downstream can trust without re-reading
     (schema rows, signatures, observed behavior, test names). Write facts,
     not prose ("report_jobs.attempts is int, 0..3, checked by
     test_retry_exhaustion" — not "the retry logic works");
   - `deviations` — planned vs actual vs why (any context expansion goes here
     too, one per expansion);
   - `newly_discovered_issues` — each with `classification` A/B/C and
     `handling` (A → fixed_in_task, B → backlog, C → escalated). Classify per
     the freeze discipline; B-class work is **never implemented** in this
     task;
   - `blockers` — for C-class stops: `CONTRACT_CHANGE_REQUEST` (contract id,
     requested change, why the current spec is wrong, evidence, proposed new
     spec) or `CORE_SEAM_BLOCKER` (seam, why structurally impossible,
     evidence); set `status: "blocked"`;
   - `verified_assumptions` — assumption ids from stage-contract.json that this
     task confirmed as true, with concrete evidence (e.g.
     `{assumption_id: "A-DB-SUPPORTS-JSON", evidence: "CREATE TABLE ran, pg_version shows 16.2"}`);
   - `falsified_assumptions` — assumption ids proven wrong, with evidence and
     implication (e.g. `{assumption_id: "A-SINGLE-NODE", evidence: "deployment uses
     two workers", implication: "retry logic must be distributed, not file-based"}`);
   - `unresolved` — questions that arose during execution but weren't blockers,
     each with `description` and `blocking: false`;
   - `scope_deviations` — planned vs actual scope with reason (higher-level than
     per-file deviations; e.g. "planned: implement C1+C2 only, actual: also had
     to update C3 registration because it depended on C2 shape");
   - `budget_used` — coarse resources consumed (compactions, wall_time_seconds,
     tokens, subagents) — used for drift and replan budget accounting;
   - `next_stage_inputs` — what this checkpoint exports for the next stage, each
     as `{input: "verified C2 api contract", artifact: "checkpoints/T01.json"}`;
   - `remaining_dag` — task ids still outstanding downstream (from the DAG);
   - `downstream_notes` — what consumers must know that is not in any
     contract (a trap you found, a fixture quirk, a timing behavior).
3. Gate: `plan-check.py validate` the checkpoint file.
4. If `status: blocked` or any blocker exists → **stop**. Report the blocker
   to the execution orchestrator / user. Do not continue working around a C
   classification.
5. **Drift check.** Compare what you built against the stage contract. Fill
   `drift` (optional, write only if any field is non-empty):
   ```json
   "drift": {
     "requirements_removed": [],
     "scope_added": [],
     "frozen_decisions_changed": [],
     "delivery_profile_changed": false,
     "acceptance_changed": [],
     "budget_envelope_changed": false
   }
   ```
   Task reorder, route adjustment, and spike insertion do NOT count as drift.
   Only changes that move outside the Project Contract corridor count.
   If `frozen_decisions_changed` or `acceptance_changed` is non-empty, the
   checkpoint MUST set `status: "blocked"` and escalate — these require a
   replan.

## Recursive Plannability

At stage completion, the checkpoint set must answer:

1. **Stable checkpoint exists?** — Every completed task has a checkpoint with
   `verified_facts` and `contracts_satisfied`.
2. **Shared contracts consistent?** — Contracts satisfied by earlier tasks are
   still true; no later task falsified an assumption an earlier task verified.
3. **No hidden half-state?** — All `changed_paths` are committed; no task left
   partial edits without a checkpoint.
4. **Next-stage inputs identifiable?** — `next_stage_inputs` in each checkpoint
   names what the next stage needs.
5. **Remaining project acceptance reachable?** — Even with deviations, the
   project's acceptance criteria are still achievable (possibly with scope
   adjustment — that's the replan controller's job).

If any answer is "no", the stage is not plannable-recursive. The
stage-checkpoint is then written with `status: "blocked"` (or
`replan_required`) recording which check failed — the next stage does not
plan on top of a failed gate.

## Heuristics

- `verified_facts` is the checkpoint's real product — budget your effort
  there; it is what makes the next agent's Required Context smaller.
- One checkpoint per stable subgoal, not per test run; "stable" = the last
  checkpoint's `verified_facts` are all still true at this point.
- `changed_paths` outside owned paths is the canary for scope creep in
  execution — when it happens, stop and classify (A or C), never "just
  commit it".
- A blocked checkpoint is a **good** checkpoint: it stops the expensive
  behavior (out-of-scope architecture repair) exactly where the freeze
  discipline says it must stop.
- A falsified assumption is more valuable than a perfectly green checkpoint:
  it saves the next stage from building on a wrong foundation. Report it
  immediately.
- `drift` is a factual record, not a judgment. If scope grew, write it in
  `scope_added` — the replan controller evaluates whether the corridor was
  exceeded.

## Output

`<plan-dir>/checkpoints/<task-id>.json` (schema `planning/checkpoint@2`).
Multiple checkpoints per task are allowed (one file, re-written as the task
advances; keep the latest).

## Failure & Escalation

- Unhealthy-run termination condition met (see execution protocol) → stop with
  `status: blocked` + stop-report content in `downstream_notes`
  (reproducer, diagnosis, failed attempts, recommended split/escalation).
- Blocker of class C → the planning layer owns the next step; in V1 that means
  stop + present to the user (replan-controller is interface-reserved).
- Checkpoint cannot express a real deviation → stop and report; an
  unexpressable deviation means the plan's vocabulary is missing something.

## Examples

**Good (T01 job store, complete).**
`{status: complete, contracts_satisfied: [C1, C5], changed_paths:
[app/db/models.py, app/services/job_store.py, alembic/versions/2026_..._report_jobs.py,
tests/services/test_job_store.py], tests: {passed: [test_create_get, test_transition_rejects_illegal,
test_recover_stale_picks_up_running], failed: [], evidence: "pytest tests/services/test_job_store.py -q → 12 passed"},
verified_facts: ["report_jobs rows: id uuid pk, status enum queued|running|retry_wait|done|failed, attempts 0..3,
progress int 0..100", "JobStore.transition raises IllegalTransition on queued→done (asserted by
test_transition_rejects_illegal)", "recover_stale(now) re-queues rows with status running and
updated_at < now - 300s"], deviations: [], newly_discovered_issues:
[{id: N1, description: "legacy csv export in app/api/routes/legacy.py duplicates job-like polling logic",
classification: B, handling: backlog}], blockers: [], remaining_dag: [T02, T03, T04, T05, T06, T07],
downstream_notes: "test db fixture uses testcontainers postgres; recovery tests need the same fixture, do not
add a sqlite fallback"}`

**Anti-pattern.** `{status: complete, completed: "done, tests pass", verified_facts: [],
changed_paths: []}` — no facts, no paths, no contracts; the next agent must
re-read everything, which is exactly the failure the checkpoint exists to
prevent.
