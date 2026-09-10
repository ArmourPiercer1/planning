# Execution Handoff — P1-v1.1-r1 (notification-retry)

**Plan dir:** `evals/probes/runs/p1-v1.1-r1/plan/`
**Stage ID:** `p1-notification-retry`
**Governor action:** `EXECUTE` (governor-decision.json, round 2)
**Delivery profile:** alpha
**Repo revision:** `790b314d1d8780b679c7f585d95c5eb3d2b6640d`

## Execution Order

From `dag.json` parallel groups and integration gates:

| Group | Task | Type | Notes |
|-------|------|------|-------|
| 1 | T01 | leaf | Retry implementation + tests. Run first. |
| 2 | T02 | e2e_closure (merged final_acceptance) | Integration gate. Runs after T01. |

**Critical path:** T01 → T02 (verification edge). No parallelism — single leaf + gate.

## Task Dispatch

### T01 — Retry implementation

Run `tasks/T01.json` with a fresh agent. It reads only the package + its `required_context.files`:
- `app/notify.py` (modify: add retry loop)
- `app/provider.py` (read-only: ProviderClient/ProviderResponse)
- `app/db.py` (read-only: NotificationStore)
- `tests/test_notify.py` (extend: 3 new test methods)
- `tests/test_gateway_observed.py` (read-only: 429 reference)

Frozen contracts C1/C2/C3 are inlined in the package with source hashes — the executor never opens `stage-contract.json`.

### T02 — E2E closure gate

Run `tasks/T02.json` with a fresh agent after T01 completes and its checkpoint is written. It runs the full test suite and verifies A1–A5. It owns `tests/test_notify.py` and may patch test assertions (not `app/notify.py`) if a defect is found.

## Execution Protocol

See `references/execution-protocol.md` (in the planning skill). Key rules:
- Each task runs in a fresh agent with no shared conversation context.
- The executor reads the task package + `required_context.files` and starts.
- Checkpoints are written after each task: `checkpoints/T01.json`, `checkpoints/T02.json`.
- The stage is complete when T02's checkpoint confirms all acceptance criteria pass.

## Escalation Paths

- **Blocker** (contract change needed, core seam broken): write a `CONTRACT_CHANGE_REQUEST` or `CORE_SEAM_BLOCKER` via `checkpoint-handoff` and stop the affected branch.
- **Unhealthy run** (repeated gate failure, budget exceeded): stop-report to the orchestrator. No silent continuation.
- **Frozen assumption falsified** (e.g., A-429-TRANSIENT invalidated by new evidence): trigger `next_planning_trigger.early` → replan.

## Spikes

None. The 429 uncertainty was resolved during planning via the in-repo staging capture (`tests/test_gateway_observed.py`). No bounded probes needed before execution.

## Deferred Findings

From `governor-decision.json` (action: EXECUTE):

| ID | Severity | Routing | Summary |
|----|----------|---------|---------|
| F02 | MINOR | OPTIONAL | C1 spec says "1+2+4 = 7s" but 3 attempts = 2 sleeps (3s). Executor will implement 2 sleeps from "3 attempts." |
| F03 | MINOR | OPTIONAL | Evidence commands use `pytest` but repo uses stdlib `unittest`. Executor should use `python -m unittest`. |
| F04 | MINOR | OPTIONAL | 4× VAGUE_ACCEPTANCE heuristic false positives. Evidence is in the `evidence` field. Cosmetic. |

## Budget Status (at execution start)

| Resource | Used | Limit |
|----------|------|-------|
| full_audits | 2 | 2 (at limit) |
| plan_revisions | 1 | 3 |
| planning_subagents | 1 | 5 |

## Acceptance Criteria (from stage-contract.json)

| ID | Description | Verified by |
|----|-------------|-------------|
| A1 | First-attempt success: 202 → status='sent', attempts=1 | T02: existing test + attempts==1 assertion |
| A2 | Retry succeeds on 2nd attempt: 500→202 → status='sent', attempts=2 | T02: test_retry_succeeds_second_attempt |
| A3 | All 3 attempts fail: 500×3 → status='failed', attempts=3, 1 record | T02: test_all_attempts_fail |
| A4 | 429 is retryable: 429→202 → status='sent', attempts=2 | T02: test_429_is_retryable |
| A5 | Existing 3 tests pass without modification | T02: full test suite green |
