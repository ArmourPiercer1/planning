# Case Q — Cross-Stage Drift

## What this tests

A regression fixture for the failure mode where a Stage's execution drifts
beyond its project contract. Stage 1 was scoped to "add a reporting subsystem."
Stage 2's checkpoint shows work on an admin dashboard — which was explicitly
a non-goal in the original contract.

## The trap

Without drift checking, scope expansion happens silently: the Stage completes,
the dashboard is half-built, but the original reporting goals may be deprioritized
or abandoned. The project contract is effectively rewritten mid-flight.

## What v1.1 fixes

- **Drift detection** — checkpoint compares `scope_added`, `requirements_removed`,
  and `acceptance_changed` against the project contract
- **Frozen decision tracking** — `frozen_decisions_changed` flags when Stage 2
  contradicts Stage 1's frozen assumptions
- **Replan trigger** — significant drift requires a replan review before Stage
  completion is accepted

## Scoring

| Criterion | Weight | Description |
|-----------|--------|-------------|
| scope_drift_detected | 3 | scope_added in drift is non-empty |
| frozen_decision_drift | 2 | frozen_decisions_changed tracked if applicable |
| replan_triggered | 3 | drift causes checkpoint to require replan review |
