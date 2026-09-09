# Planning Skills v1.1 — Post-Completion Summary

**Commit:** `d4145b5` on `main`
**Date:** 2025-07-18
**Packages:** A–G (7 implementation packages, 28 files, +1249 lines)

---

## 1. New Workflow

Pipeline extended from 8 to 9 stages:

```
stage-0: repo-context-snapshot       (existing)
stage-1: stage-contract              (extended: delivery_profile, planning_budget, horizons)
stage-2: context-decomposer          (unchanged)
stage-3: dependency-dag              (unchanged)
stage-4: integration-planner         (unchanged)
stage-5: task-packager               (unchanged)
stage-6: plan-risk-estimator         (extended: schedule is forecast)
stage-7: plan-auditor                (extended: delivery-profile-gated, DO NOT AUDIT FOR)
stage-8: planning-governor           (NEW: routes findings, enforces budget)
          ↓
    EXECUTE → handoff + execution
    SPIKE → bounded probe → re-audit
    TARGETED_PATCH → fix → re-audit
    HUMAN_BLOCKER → stop + escalate
```

Key constraint: The revision loop must NOT spawn new reviewers. Budget (max 2 full audits, max 3 revisions, max 5 subagents) enforced by governor. When exhausted, HUMAN_BLOCKER.

---

## 2. New Schemas

| Schema | File | New in v1.1 |
|--------|------|-------------|
| `planning/governor-decision@1` | `governor-decision.schema.json` | NEW — governor output |
| `planning/audit@3` | `audit-v3.schema.json` | NEW — routing field, delivery_profile_applied |
| `planning/stage-contract@3` | `stage-contract.schema.json` | EXTENDED — delivery_profile, planning_budget, horizons, stage_boundary, next_planning_trigger |
| `planning/checkpoint@2` | `checkpoint.schema.json` | EXTENDED — verified/falsified assumptions, drift, recursive plannability |

All schemas backward-compatible: old `@2` artifacts validate against `@3` schemas (enum allows both versions).

---

## 3. Modified / New Skills

| Skill | Change |
|-------|--------|
| `planning-governor` | **NEW** — finding taxonomy, budget enforcement, uncertainty routing, execution gate |
| `plan-auditor` | Extended — delivery-profile-gated severity, DO NOT AUDIT FOR, over_planning/missing_spike_route checks |
| `plan-risk-estimator` | Extended — schedule is forecast, not certification gate |
| `stage-contract` | Extended — delivery_profile, planning_budget, horizons (step 12), stage_boundary (step 13), next_planning_trigger (step 14) |
| `long-task-planning` | Extended — stage 8 added, revision loop guardrails, governor action routing, anti-pattern updated |
| `checkpoint-handoff` | Extended — verified/falsified assumptions, drift check, recursive plannability |
| `replan-controller` | Extended — cross-reference to governor for pre-execution gating |

---

## 4. Verification Results

| Test | Result |
|------|--------|
| plan-check.py selftest | OK |
| good-plan lint (regression) | 0 BLOCKER, 0 MAJOR, 0 MINOR |
| bad-plan lint (defect detection) | 9 codes detected |
| minimal_fixes tests | 6/6 PASS |
| v11 integration test | PASS |

---

## 5. Current Items Still Requiring Prompt Discipline

These capabilities are defined in the skill but rely on the model following instructions rather than being enforced by deterministic checks:

1. **Budget enforcement** — The governor SKILL.md instructs the agent to check `planning_budget.max_full_audits` and issue HUMAN_BLOCKER when exceeded. The model must actually count and check these numbers. A future runtime could enforce this via a plugin counter.

2. **Horizon discipline** — The stage-contract skill instructs "forecast stages get no Task Packages." The model must resist the urge to over-plan. Schema validates the structure but cannot prevent the agent from populating forecast with detailed tasks.

3. **DO NOT AUDIT FOR** — The plan-auditor skill lists topics the auditor must not flag. The auditor is a language model — it may still produce these findings unless a runtime filter intercepts them.

4. **Delivery profile gating** — The auditor must judge whether "rich UI polish" is "not required for alpha." This is a semantic judgment. A runtime could provide a lookup table.

5. **Stage boundary selection** — The skill lists 7 heuristics for where to end a stage. The actual boundary decision is a model judgment call.

6. **Spike routing** — The governor routes "public seam feasibility" to spike. The quality of the spike probe description depends on the model's ability to design a minimal test.

7. **Drift check** — The checkpoint skill instructs recording drift. The agent must honestly compare what it built against the contract. A future runtime could diff the actual scope against the declared scope.

---

## 6. Capabilities Most Worth Sinking to Runtime/Plugin

Ranked by impact and feasibility:

### Highest Priority
1. **Planning budget enforcement** — A `planning-budget` plugin that tracks audit count, revision count, and subagent count. When limits are exceeded, the plugin blocks the next planning action and forces HUMAN_BLOCKER. This is the single most impactful runtime addition.

2. **Governor decision gate** — A plugin that intercepts the plan-audit→execution transition and requires `governor-decision.json` with `action: EXECUTE` before dispatching. Prevents the planner from skipping the governor.

3. **Checkpoint drift checker** — A script (like `plan-check.py`) that diffs the stage contract against checkpoint `drift` fields and flags corridor violations. Already partially supported by the `drift` schema.

### Medium Priority
4. **Horizon validator** — A lint check that verifies forecast stages have no Task Packages and no detailed DAG edges. This could be added to `plan-check.py` lint.

5. **Next planning trigger monitor** — A runtime that watches for the trigger conditions listed in `next_planning_trigger.early` and automatically invokes the planner. Currently requires manual detection.

### Lower Priority (V2)
6. **Finding taxonomy interceptor** — A filter that prevents the auditor from emitting findings about topics in "DO NOT AUDIT FOR."
7. **Delivery profile lookup table** — A deterministic table mapping delivery profile level → findings that are auto-demotion candidates.

---

## Definition of Done Checklist

### Planning Governance ✅
- [x] planning budget 是一等字段 (stage-contract@3)
- [x] workflow 无无界 audit/replan loop (revision guardrails)
- [x] EXECUTION_BLOCKER / SPIKE_REQUIRED / POST_STAGE / OPTIONAL (governor skill)
- [x] public seam/runtime uncertainty 能路由到 spike (uncertainty routing table)
- [x] delivery profile 影响 audit severity (auditor SKILL.md)
- [x] schedule over-target 不再自动导致无限 replan (risk-estimator revision)

### Horizon Awareness ✅
- [x] Project Contract 与 Current Stage Plan 分离 (horizons field)
- [x] commitment / detailed / forecast 三 horizon (horizons schema)
- [x] future forecast 不展开 leaf DAG (skill instruction)
- [x] Stage Plan 包含明确 stop boundary (stage_boundary)
- [x] 能输出"为什么只计划到这里" (stage_boundary.because)
- [x] next_planning_trigger 存在 (stage-contract@3)

### Continuity ✅
- [x] Checkpoint 记录 verified/falsified assumptions (checkpoint@2)
- [x] Drift checker 能发现 scope/acceptance/frozen decision 漂移 (drift field)
- [x] Stage completion 有 recursive-plannability 检查 (5-check gate)

### Evals ✅ (fixtures only)
- [x] Case M–Q 至少有可运行 fixture (15 files created)
- [x] Scoring specs defined in case.json
- [ ] time-to-first-evidence / plan churn scorer code — deferred to next phase
- [ ] Full eval comparison — requires running new vs baseline

---

*End of v1.1. Next phase: Stagewise Receding-Horizon Runtime Compatibility.*
