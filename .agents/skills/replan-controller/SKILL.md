---
name: replan-controller
description: INTERFACE RESERVED in V1. Defines when replanning may fire (only predefined triggers — unhealthy run, blocker, repeated gate failure, contract error) and the closed legal action set (split, merge, reorder, change_dependency, defer, reduce_scope, replace_route, checkpoint_and_split, request_contract_revision), with append-only replanning explicitly forbidden. In V1 this skill is invoked only to produce the structured replan-request and to stop the affected branch for a user decision; no autonomous re-planning. Use when an execution trigger fires during a /long-task-planning Stage.
---

# replan-controller

Replanning is a **legal move**, and only some moves are legal. This skill is
the gate between "something went wrong" and "the plan changes". **V1 status:
interface reserved** — the formats, triggers, and action set below are the
contract that V2 will implement autonomously; in V1 the outcome of a triggered
replan is always *stop + structured request + user decision*. **In v1.1 the
`planning-governor` subsumes the pre-execution replan-gate role: the governor
decides EXECUTE / SPIKE / TARGETED_PATCH / HUMAN_BLOCKER before execution
starts. The replan-controller remains the gate for *in-execution* replan
triggers (unhealthy run, blocker, gate failure, contract error).**
Vocabulary:
`../../references/glossary.md`.

## Trigger (closed set — no ad-hoc replans)

A replan may be initiated **only** by:

1. **unhealthy_run** — a stop-report from the execution protocol (any of the
   six unhealthy-run conditions);
2. **blocker** — a checkpoint with `CONTRACT_CHANGE_REQUEST` or
   `CORE_SEAM_BLOCKER`;
3. **gate_failure** — the same acceptance gate failed 3 consecutive attempts;
4. **contract_error** — a frozen contract proved wrong during execution
   (evidence: test failure that the contract's spec makes impossible to fix
   in-task).

Anything else ("feels too big", "new idea") is **not a trigger** — it is a B
class issue or a user decision.

## Inputs

- The triggering artifact (stop-report, checkpoint, gate log);
- the current plan directory (contract, DAG, packages, risk estimates).

## Procedure (V1 behavior; V2 extends steps 2–4)

1. **Classify** the trigger and copy its evidence verbatim into the request
   (`trigger.kind`, `trigger.evidence`, `trigger.source`).
2. **Propose actions** from the **closed legal set**: `split`, `merge`,
   `reorder`, `change_dependency`, `defer`, `reduce_scope`, `replace_route`,
   `checkpoint_and_split`, `request_contract_revision`. Each action names
   `target_task`, `detail`, and `scope_delta` (`none` / `reduced` /
   `expanded_needs_user_approval`).
   - First question for any failure: is there a **split** or
     **replace_route** that keeps scope constant? Propose append-only growth
     last, and only with `scope_delta: expanded_needs_user_approval`.
   - `request_contract_revision` is the only path that touches frozen
     contracts; it must quote the offending contract id and the evidence.
3. **Append-only check** — set `append_only_rejected: true` only if the
   proposal reshapes or shrinks work (adds ≥ 1 action that is not pure task
   addition). A proposal that only adds tasks is rejected at this step;
   re-derive.
4. **Write** `replan-requests/<seq>.json` (schema
   `planning/replan-request@1`, `status: proposed`), gate with
   `plan-check.py validate`.
5. **V1 stop.** Present the request to the user/orchestrator and wait. No
   pipeline stage is re-run, no task is re-dispatched, until the request is
   explicitly approved (or the user gives an equivalent decision).
6. (V2, reserved.) On approval, re-run only the pipeline stages owning the
   changed tasks (per the orchestrator's revision map), then re-audit
   (fresh isolated auditor), and update `run-manifest.json`.

## Heuristics

- Replan should be able to **shrink** the plan; a skill set where replan only
  grows work is the degenerate "found problem → append task" mode this skill
  forbids.
- `checkpoint_and_split` is the default for oversized-leaf triggers: the
  completed subgoals stand, the remainder is re-planned from the checkpoint —
  local recoverability applied to the plan itself.
- Every `defer`d item gets a destination (backlog issue), not a void.

## Output

`<plan-dir>/replan-requests/<seq>.json` (schema `planning/replan-request@1`).

## Failure & Escalation

- The trigger is not in the closed set → do not create a request; route the
  item to B-class backlog or to the user as a scope question.
- A proposal cannot avoid `scope_delta: expanded_needs_user_approval` → mark
  it and stop at the user; scope growth is never an executor or planner
  unilateral move.
- (V2) Approved replan that fails re-audit → same 3-round bound as the
  initial audit; then escalate.

## Examples

**Good.** T02 (runtime worker) hits attempt 3 failing the same retry gate →
`{trigger: {kind: unhealthy_run, evidence: "3 attempts, same failure:
test_retry_exhaustion — worker re-enters queued after retry_wait without
backoff", source: checkpoint}, proposed_actions:
[{action: checkpoint_and_split, target_task: T02, detail: "keep completed
subgoal 'pool + state transitions' (checkpoint T02-cp1), re-plan the
retry/backoff sub-closure as new leaf T08 with C3+retry-table context only",
scope_delta: none}, {action: request_contract_revision, target_task: C3,
detail: 'state machine lacks "retry attempt recorded at transition, not at
completion" — quote C3 spec vs test evidence', scope_delta: none}],
append_only_rejected: true}`

**Anti-pattern.** "T02 is hard, so we also add T09 'general worker
hardening', T10 'logging improvements', T11 'config refactor'" — pure
append-only growth from a single failure; `append_only_rejected` would be
false and the request is rejected at step 3.
