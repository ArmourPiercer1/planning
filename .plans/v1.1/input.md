
# Planning Skills v1.1 — Planning Governance & Horizon Awareness MVP

## Problem

Planning Skills currently have no mechanism to stop meta-planning runaway: repeated plan-audit-replan cycles can spawn 30+ subagents, consume 100M+ tokens, and never reach implementation. There is also no "planning horizon awareness" — the planner cannot say "I only plan this far; the rest depends on evidence we don't have yet."

## Objective

Add two capabilities without推翻 the existing pipeline:

1. **Planning Behavior Control** — budget caps, governor routing, finding taxonomy that prevents audit recursion.
2. **Planning Horizon Awareness** — commitment/detailed/forecast horizons, stage boundaries, next-planning triggers.

## Scope

Only Planning Skills, schemas, scripts, skills, evals, docs. No dsh-agent-team product code changes.

## Packages (A–G)

- **A** — Stage/Project schema v3 + delivery_profile + planning_budget fields
- **B** — Planning Governor skill + finding taxonomy (EXECUTION_BLOCKER/SPIKE_REQUIRED/POST_STAGE/OPTIONAL) + uncertainty routing
- **C** — Audit v3 finding routing + auditor/risk/schedule behavior revision
- **D** — Horizon awareness: commitment/detailed/forecast + stage boundary + next_planning_trigger
- **E** — Checkpoint v2 + drift checker + recursive plannability
- **F** — Workflow/orchestrator integration of governor into pipeline
- **G** — New eval fixtures (cases M–Q), scorers, telemetry fields, regression suite
