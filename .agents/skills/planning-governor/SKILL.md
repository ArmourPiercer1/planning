---
name: planning-governor
description: Classify audit findings into execution-routing categories (EXECUTION_BLOCKER, SPIKE_REQUIRED, POST_STAGE, OPTIONAL), enforce planning budget constraints, route uncertainties to bounded probes, and decide whether to EXECUTE, SPIKE, TARGETED_PATCH, or escalate as HUMAN_BLOCKER. Runs after plan-auditor and before execution dispatch. Use as the gate between planning and execution, or at checkpoint decision points.
---

# planning-governor

Route audit findings to the correct action instead of using pure
BLOCKER/MAJOR/MINOR severity. The auditor finds — the governor decides what
to do. This prevents planning/review/replan from becoming an unbounded
meta-task, and stops "not sure yet" from blocking execution.

Vocabulary: `../../references/glossary.md`.

## Trigger

- **Use:**
  - (a) After initial plan + audit complete, before execution dispatch
  - (b) After a targeted revision round
  - (c) At a stage checkpoint when deciding whether to continue/replan
- **Do NOT use:**
  - After every worker completes (use `checkpoint-handoff` instead)
  - As a substitute for `plan-auditor` (the governor routes; it does not audit)
  - To run another full audit loop (use `replan-controller` for replan
    actions, within budget limits)

## Inputs

- The complete plan directory (all artifacts from the pipeline)
- `audit.json` — findings from the latest plan-auditor pass
- `stage-contract.json` — `planning_budget` (if present), `delivery_profile`
  (if present), `integration_seams`, `acceptance` criteria
- `risk-estimates.json` — per-task risk including p50/p80 ranges
- Planning telemetry (if available):
  - `agents_used` — number of planning subagents started
  - `plan_revisions` — count of plan revisions (append-only)
  - `full_audits` — count of full auditor passes
  - `tokens` — token budget consumed during planning
  - `wall_time` — wall-clock time spent in planning

## Procedure

### Step 1 — Classify findings into routing categories

Read every finding from `audit.json`. Replace pure BLOCKER/MAJOR/MINOR
severity with routing-aware categories:

#### EXECUTION_BLOCKER

Only classify as EXECUTION_BLOCKER when continuing would cause an irreparable
failure. The bar is high. A finding qualifies ONLY if it satisfies one of:

- Continuing would cause core acceptance failure (reference a specific
  acceptance criterion that cannot be met)
- Known security, permission, or data integrity violation
- Missing不可绕开的 (unbypassable) public seam that blocks execution
- Requires the user to re-decide product semantics
- Durable state corruption risk (data loss, broken migration path)
- Current architecture fundamentally cannot carry the core objective

**Guardrail:** A finding that cannot reference a specific stage acceptance
or a project hard invariant **cannot** be EXECUTION_BLOCKER. If you are
unsure, route it to SPIKE_REQUIRED or POST_STAGE instead.

#### SPIKE_REQUIRED

Classify here when the question can be answered by a bounded executable
probe (~60–90 min). Common cases:

- Public seam feasibility question (does this API exist? does it accept our
  input format?)
- Runtime behavior question (does this function actually block? what's the
  actual latency?)
- Integration behavior question (do modules A and B actually wire together
  without conflict?)
- Performance assumption question (can this handle the target throughput?)

**Hard rule:** If a question can be answered by a ~60–90 min executable
test/spike, it MUST be routed here — not to more LLM review. "Not sure yet"
is not a blocker; it is a spike.

#### POST_STAGE

The finding is correct but does not block the current stage. Examples:

- Future-stage concern (design of Stage N+1's internal structure)
- Optimization that would require more evidence before committing
- Cleanup/refactoring not in scope for this delivery profile
- Enhancement that is outside the current stage boundary

#### OPTIONAL

Nice-to-have, optimization, cleanup, or future possibility. Examples:

- Code style consistency improvements
- Additional test coverage beyond delivery profile
- Documentation polish
- Future feature suggestions

### Step 2 — Check planning budget

Read `planning_budget` from `stage-contract.json` if present. Apply hard
limits:

```yaml
planning_budget:
  max_full_audits: N        # if current audit count >= limit, forbid more
  max_plan_revisions: N     # if current revision count >= limit, force HUMAN_BLOCKER
  max_planning_subagents: N # if agent count >= limit, forbid spawning
```

**Default heuristics** (when no explicit `planning_budget`):
- `max_full_audits`: 2 (initial + 1 pre-execution replan)
- `max_plan_revisions`: 3
- `max_planning_subagents`: 5

Actions:
- If `full_audits >= max_full_audits`: add `"launch_another_full_audit"` to
  `forbidden_actions`
- If `plan_revisions >= max_plan_revisions`: force `HUMAN_BLOCKER`
- If `agents_used >= max_planning_subagents`: add `"spawn_planning_subagent"`
  to `forbidden_actions`

### Step 3 — Route uncertainties

For each finding or open question that represents genuine uncertainty
(instead of a concrete defect), classify its uncertainty type and assign a
route:

| Uncertainty Type | Default Route |
|---|---|
| `ARCHITECTURE_DECISION` | bounded reasoning, escalate to Human if semantic |
| `REPOSITORY_FACT` | bounded read (read specific files to confirm) |
| `PUBLIC_SEAM_FEASIBILITY` | spike (executable test of the API) |
| `RUNTIME_FACT` | spike / measurement (run code, measure result) |
| `OPTIONAL_FEATURE` | defer to POST_STAGE or OPTIONAL |
| `EXTERNAL_BLOCKER` | EXECUTION_BLOCKER (upstream dependency, access) |

Record each routed uncertainty in the `spikes` or `deferred` output
array. For spike-routed items, include:
- `probe_description`: what exactly to test
- `success_criteria`: observable outcome that resolves the uncertainty

### Step 4 — Decide action

Apply the decision logic in order:

```
1. if any EXECUTION_BLOCKER findings exist → HUMAN_BLOCKER
2. if any SPIKE_REQUIRED findings exist → SPIKE
3. if planning budget exceeded (max_plan_revisions) → HUMAN_BLOCKER
4. if only POST_STAGE + OPTIONAL findings → EXECUTE
5. otherwise → EXECUTE
```

`TARGETED_PATCH` is used when the findings are concrete, narrow defects that
can be fixed in-place (one revision pass) without a full replan — e.g., a
single task's acceptance criterion is wrong, or an owned path collision
exists. The governor may trigger this when:
- Findings are all MAJOR severity
- At most 2 findings
- Each affects exactly one artifact
- No EXECUTION_BLOCKER or SPIKE_REQUIRED

### Step 5 — Schedule feasibility

If `risk-estimates.json` shows aggregate P80 exceeds the user's target
budget:

1. Allow at most **ONE** scope-fit pass (cut lowest-priority items)
2. Re-forecast after the cut
3. If still over target: output `likely_checkpoint`, `cut_rules`,
   `residual_uncertainty`, and `expected_range` in the reason field
4. **Do NOT** force a replan loop — schedule is a forecast, not a
   certification gate

Execution may proceed if there are no EXECUTION_BLOCKER findings, even if
the schedule forecast is over target. Record the forecast risk in the
governor's reason.

## Output

Write `<plan-dir>/governor-decision.json` (schema `planning/governor-decision@1`).

The action field is one of:
- `EXECUTE` — proceed with execution
- `SPIKE` — run bounded probes first
- `TARGETED_PATCH` — fix narrow defects in-place
- `HUMAN_BLOCKER` — escalate to user

```json
{
  "schema": "planning/governor-decision@1",
  "action": "EXECUTE",
  "blocking_findings": [],
  "spikes": [],
  "deferred": [],
  "planning_budget_status": {
    "plan_revisions": 0,
    "full_audits": 1,
    "subagents": 2,
    "wall_time": null,
    "tokens": null
  },
  "forbidden_actions": [],
  "reason": "Audit found 0 execution blockers, 0 spikes required. Planning within budget (1 audit, 0 revisions). Proceeding to execution."
}
```

Validate with `plan-check.py validate` against the schema.

## Heuristics

- **Governor does not audit — it routes.** The auditor finds, the governor
  decides what to do. Do not add new findings; classify existing ones.
- **High bar for EXECUTION_BLOCKER.** A finding that cannot reference a
  specific stage acceptance criterion or a project hard invariant cannot be
  an execution blocker. When in doubt, spike or defer.
- **"Not sure yet" is not a blocker.** It is a spike or a defer. The whole
  point of this skill is to stop uncertainty from stalling execution.
- **Bounded spikes over more planning.** If a ~60–90 min executable test
  can answer a question, route to SPIKE. Do not spawn another planner.
- **Delivery profile matters.** An alpha-level stage does not need
  production-grade assurance. A finding about missing migration matrix is
  POST_STAGE for alpha, but could be EXECUTION_BLOCKER for RC.
- **Budget is real.** When the planning budget is exhausted, stop planning
  and escalate. The user decides whether to increase the budget or proceed
  with current information.

## Examples

**Example 1: Clean plan, proceed to execution**

Audit found 1 MINOR finding about acceptance text style. No EXECUTION_BLOCKER,
no SPIKE_REQUIRED. Planning budget well within limits.

```json
{
  "action": "EXECUTE",
  "blocking_findings": [],
  "spikes": [],
  "deferred": [
    {"finding_id": "F01", "routing": "OPTIONAL", "reason": "acceptance text style cleanup — does not affect execution correctness"}
  ],
  "planning_budget_status": {"plan_revisions": 0, "full_audits": 1, "subagents": 2},
  "forbidden_actions": [],
  "reason": "0 execution blockers, 0 spikes. 1 minor style finding deferred. Budget OK. Executing."
}
```

**Example 2: Public seam unknown — route to spike**

Audit found MAJOR: "C1 contract requires API endpoint that may not exist."
This is a PUBLIC_SEAM_FEASIBILITY question answerable by reading the router
file.

```json
{
  "action": "SPIKE",
  "blocking_findings": [],
  "spikes": [
    {
      "finding_id": "F03",
      "uncertainty_type": "PUBLIC_SEAM_FEASIBILITY",
      "probe_description": "Read app/api/routes/ to verify whether GET /profiles/{id} route exists or needs creation. Check if FastAPI router supports path parameters.",
      "success_criteria": "Confirmed whether the route pattern exists or the router supports it"
    }
  ],
  "deferred": [],
  "planning_budget_status": {"plan_revisions": 0, "full_audits": 1, "subagents": 2},
  "forbidden_actions": [],
  "reason": "1 public seam feasibility question routed to spike (~30 min probe). No execution blocker. Spike result will determine whether targeted patch or clean execution."
}
```

**Example 3: Budget exceeded — human block**

Already 3 full audits, 3 plan revisions, 6 subagents. New audit found 2
MAJOR findings. Default budget limits: 2 audits, 3 revisions, 5 subagents.
Both audit and revision counts exceed limits.

```json
{
  "action": "HUMAN_BLOCKER",
  "blocking_findings": [],
  "spikes": [],
  "deferred": [],
  "planning_budget_status": {
    "plan_revisions": 3,
    "full_audits": 3,
    "subagents": 6
  },
  "forbidden_actions": [
    "launch_another_full_audit",
    "spawn_planning_subagent"
  ],
  "reason": "Planning budget exhausted: 3/2 full audits and 6/5 subagents exceed defaults. 3 plan revisions at max. 2 remaining MAJOR findings require user judgment to resolve. Escalating — user must decide whether to increase budget or proceed with current plan."
}
```
