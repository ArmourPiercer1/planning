# Execution Protocol (for agents consuming Task Packages)

This is the contract between a finished plan and an executing agent. An
execution agent receives **one Task Package** (`tasks/<id>.json`) and follows
this protocol. It does not read the rest of the plan.

## Startup

1. Read the Task Package only. **Never open `stage-contract.json`** — all
   frozen contracts are inlined in the package's `frozen_contracts[]` with
   matching `source_hash` (BLOCKER `STALE_CONTRACT_SNAPSHOT` if the hash
   doesn't match what the current stage contract would produce; the packager
   owns that).
2. Load exactly `required_context.files` (the verbatim spec text is in
   `frozen_contracts[].spec`, not a path you resolve), and
   `required_context.concepts`.
3. If context proves insufficient mid-run: expand **one file at a time**, and
   record each expansion in the checkpoint (`deviations`, with the reason).
   A directory-wide or repo-wide read is never a quiet fallback — it is an
   unhealthy-run signal (see below).

## Freeze discipline (what to do when you find a problem)

Classify before acting — exactly one class applies:

- **A. Must fix to complete this task** → fix it; record in checkpoint
  `deviations` (planned vs actual vs why).
- **B. Worth improving, does not block this Stage** → record in checkpoint
  `newly_discovered_issues` with `classification: "B"`,
  `handling: "backlog"`. **Do not implement it.**
- **C. The frozen contract/architecture is wrong; the task cannot be done
  correctly as specified** → stop out-of-scope implementation. Emit a blocker
  in the checkpoint:
  - `CONTRACT_CHANGE_REQUEST` — contract-level fix (which contract id, what
    changes, why the current spec is wrong, evidence, proposed new spec); or
  - `CORE_SEAM_BLOCKER` — a seam is structurally impossible as designed.
  Set checkpoint `status: "blocked"` and stop. The planning layer decides;
  the executor never edits a frozen contract.

## Checkpoints (checkpoint-handoff skill)

At every **stable subgoal** — not only at the very end — write
`checkpoints/<task-id>.json` per the `checkpoint-handoff` skill. A stable
subgoal is any point where another agent could pick up from the checkpoint
alone. The checkpoint is a **context handoff artifact**: `verified_facts` must
be concrete facts downstream consumers can trust without re-reading your work
(schema rows, test names, observed behaviors), and `changed_paths` must stay
inside `owned_paths` (plus this task's tests) — anything else is a scope
violation and must be recorded as a deviation.

## Unhealthy-run termination conditions

Stop implementing and produce a **stop-report** (minimal reproducer, current
diagnosis, failed attempts, blocker, evidence, recommended split/escalation)
when any of:

1. Well past the package's P80 with no approach to closure.
2. Context churn keeps growing (repeated reads beyond `required_context`).
3. New cross-layer dependencies keep appearing.
4. Multiple compactions already occurred or are clearly imminent.
5. Three consecutive implementation attempts fail the same acceptance gate.
6. The task is forced to read far more than its Required Context.

Default behavior is **not** to keep piling implementation on.

## Scheduling (orchestrator of execution)

- Run tasks in `dag.json` parallel groups; a task starts only when all its
  incoming edges are satisfied (upstream checkpoints exist).
- Integration tasks run last, per their gates; they consume upstream
  checkpoints + contracts + changed paths — not the whole repo.
- A failed leaf: only that leaf and its downstream subgraph are invalidated.
  Unrelated branches keep running (local recoverability).

## V1 replan boundary

`replan-controller` is interface-reserved in V1: when a trigger fires
(unhealthy run, blocker, repeated gate failure), the execution orchestrator
**stops the affected branch, presents the structured stop-report/blocker to
the user, and waits**. No autonomous re-planning in V1.
