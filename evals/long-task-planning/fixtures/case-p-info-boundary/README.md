# Case P — Information-Gain Boundary

## What this tests

A regression fixture for the failure mode where the planner either:
(a) plans through the spike as if the answer is known, producing detailed
implementation plans for both routes, or (b) refuses to plan anything because
"we don't know which route to take yet."

## The trap

The correct behavior is to plan the spike as a concrete leaf task, end the
stage there, and put the two post-spike implementation routes in forecast.
The stage boundary is the information-gain point: after the spike runs, we
know which route to take.

## What v1.1 fixes

- **Spike as leaf** — the probe is a real task with acceptance criteria
- **Stage boundary at spike** — `stage_boundary.stop_after` marks the spike
- **Next planning trigger** — `stage_acceptance_reached` triggers the next planning round
- **Forecast branches** — two routes defined with dependency on spike outcome

## Scoring

| Criterion | Weight | Description |
|-----------|--------|-------------|
| spike_is_leaf | 3 | probe is a concrete leaf task |
| stage_boundary_at_spike | 3 | stage_boundary.stop_after includes spike task |
| next_planning_trigger | 2 | next_planning_trigger.normal includes stage_acceptance_reached |
| forecast_branches | 2 | two forecast stages for two routes |
