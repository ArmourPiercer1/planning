# Case N — Too-Far Planning

## What this tests

A regression fixture for the failure mode where the planner produces detailed
DAGs, Task Packages, and acceptance criteria for future phases that depend on
evidence not yet available. The result is "beautiful but soon obsolete" planning
work that gets rewritten when Phase 1 reveals new constraints.

## The trap

The temptation is to plan all three phases (reporting split, user split, event bus)
with full DAGs because "we have the architectural vision." But Phase 1 execution
will reveal integration seams, performance characteristics, and operational
constraints that make Phase 2/3 detailed plans speculative.

## What v1.1 fixes

- **Horizon awareness** distinguishes detailed (now) from forecast (later) planning
- **Stage boundary** marks where current evidence runs out
- **Forecast stages** have objective + depends_on_evidence, not full DAGs
- **No future Task Packages** are generated for forecast-stage work

## Scoring

| Criterion | Weight | Description |
|-----------|--------|-------------|
| horizon_respected | 3 | forecast stages have no detailed DAG |
| stage_boundary_set | 2 | stage_boundary.stop_after defined |
| next_planning_trigger | 2 | next_planning_trigger.normal includes stage_acceptance_reached |
| no_future_task_packages | 3 | no Task Packages for forecast stages |
