# Case M — Meta-Planning Runaway Regression

## What this tests

A regression fixture for the failure mode where planning, review, and replan
become a runaway process: the planner spawns reviewers who spawn sub-reviewers,
debating architectural questions that could be answered by reading a few files
or running a bounded spike.

## The trap

The repo has existing notification infrastructure tightly coupled to user auth.
The question "should we refactor the coupling or build around it" is an
**empirical unknown** — solvable by reading the existing code, not by
spawning reviewers to debate it.

## What v1.1 fixes

- **Planning budget** limits full audits to 2, preventing indefinite review cycles
- **Spike routing** sends empirical unknowns to bounded probes instead of reviewers
- **Finding classification** defers non-blocking items as POST_STAGE
- **Time-to-first-evidence** measures whether the first task produces real code

## Scoring

| Criterion | Weight | Description |
|-----------|--------|-------------|
| planning_budget_enforced | 3 | max_full_audits not exceeded |
| spike_routing | 3 | empirical unknown routed to spike |
| deferred_nonblockers | 2 | POST_STAGE items deferred |
| time_to_first_evidence | 2 | first executable evidence within budget |
| no_append_only_growth | 2 | plan did not grow via append-only replan |
