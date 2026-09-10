# 下一版本 Planning Skills 详细开发指导
## v1.1 — Planning Governance & Horizon Awareness MVP

> **这份文档可以直接作为下一版本本地 Agent 的启动指导。**

---

# 0. 任务定义

你现在要升级现有 **Long-Task Planning Skills**。

本版本不推翻已有的：

```text
contract-first
context-bounded decomposition
dependency DAG
task packages
integration planning
checkpoint/handoff
local recoverability
```

而是在其上修复一次已经真实发生的严重 failure mode：

> Planning Skills 在一个约 24h 的成熟仓库增量任务上，多轮 plan/audit/replan 后拉起 30+ subagent，消耗超过 100M token，仍长期没有进入 implementation；随着 reviewer 不断发现新的合理问题，计划不断扩张、scope 不断削减、预测工期不断增加。

本版本必须解决两个核心问题：

1. **Planning Behavior Control**  
   防止 planning / review / replan 自己成为长任务失控源。
2. **Planning Horizon Awareness**  
   Planner 能明确判断：
   > “我现在只应该详细计划到这里；完成这个 Stage / 获得这些证据后再规划下一阶段。”

本版本完成后，Planning Skills 应能在大部分边界清楚的软件工程任务上生成足够可靠且成本受控的阶段计划。

**本版本只改 Planning Skills / schemas / workflow / evals / docs。不要顺手修改 dsh-agent-team 产品代码。**

---

# 1. 先读取并审计现有实现

开始修改前，读取当前仓库中实际存在的：

```text
Long-Task Planning Skills
Stage Contract schema
Task Package schema
planning workflow/orchestrator
plan-auditor
plan-risk-estimator
checkpoint-handoff
replan-controller（如果已实现）
planning evals
runner/scorers
planning challenge fixtures
```

同时读取现有方法论来源：

- `long_task_planning_skills_bootstrap.md` 或仓库中对应设计；
- `long_task_planning_evals_bootstrap.md` 或对应 eval 设计；
- 当前实际 SKILL.md / scripts / schemas / tests。

不要假设 bootstrap 文档就是当前实现。

输出一个很短的：

```text
CURRENT IMPLEMENTATION MAP
```

只说明：

```text
EXISTS
PARTIAL
MISSING
```

不要开启新一轮大型 architecture review。

---

# 2. 本版本硬约束

## 2.1 不允许 Meta-Planning Runaway

本版本开发本身也必须遵守：

```text
主 Agent + 最多 1 个初始 focused plan reviewer
不允许 audit → audit 的递归回路
普通未知优先 spike/test，而不是追加 planner
```

如果开发计划本身开始：

```text
> 12 implementation packages
> 3 full planning audits
> 15 distinct subagents
```

立即检查是否重复了待修复 failure。

---

## 2.2 不建立完整 runtime controller

本版本不要实现：

```text
dsh-agent-team Project/Stage durable state machine
automatic long-running planner daemon
learned model router
learned Value-of-Computation
automatic adaptive horizon optimizer
complex plugin UI
```

这些留给后续 runtime compatibility 阶段。

---

# 3. 目标架构

现有主流程从：

```text
stage-contract
→ context-decomposer
→ dependency-dag
→ task-packager
→ risk-estimator
→ plan-auditor
→ targeted revision
→ audit ...
→ execution
```

改成：

```text
Project / Stage Contract
      ↓
Context + DAG + Task Packaging
      ↓
One Plan Audit
      ↓
Planning Governor
   ┌──────┬────────────┬─────────────┐
   │      │            │             │
EXECUTE  SPIKE   TARGETED_PATCH  HUMAN_BLOCKER
   │      │            │
   │   executable      │
   │    evidence       │
   └──────┴────────────┘
             ↓
       Current Stage
             ↓
        Checkpoint
             ↓
     Next-Planning Trigger
```

**禁止 plan-auditor 自己直接造成新的 full-plan-audit loop。**

---

# 4. Workstream A — `planning-governor`

这是本版本最重要的新能力。

如果仓库已有 `replan-controller`，优先升级/重构为 governor，而不是平行制造重复 skill。

## 4.1 Trigger

在以下时机调用：

```text
初始 plan + audit 完成后
targeted revision 后
Stage checkpoint 需要判断是否继续/重规划时
```

不要在每个 worker 完成后调用。

---

## 4.2 输入

至少：

```yaml
project_contract:
stage_plan:
audit_findings:
planning_telemetry:
  agents_used:
  plan_revisions:
  full_audits:
  tokens_if_available:
  wall_time_if_available:
delivery_profile:
budget:
```

---

## 4.3 Finding 分类

废弃仅靠：

```text
BLOCKER / MAJOR / MINOR
```

作为执行路由。

新增：

```text
EXECUTION_BLOCKER
SPIKE_REQUIRED
POST_STAGE
OPTIONAL
```

### EXECUTION_BLOCKER

只有以下类问题：

```text
继续实现必然导致核心 acceptance 失败
已知权限/安全/数据完整性破坏
缺失无法绕开的 public seam
需要用户重新决定产品语义
durable state corruption 风险
当前架构根本无法承载核心目标
```

### SPIKE_REQUIRED

可通过有限 executable probe 快速求解：

```text
public seam feasibility
runtime behavior
integration behavior
performance assumption
```

### POST_STAGE

正确但不阻塞当前 Stage。

### OPTIONAL

优化/清理/未来可能性。

---

## 4.4 输出

建议：

```yaml
governor_decision:
  action: EXECUTE | SPIKE | TARGETED_PATCH | HUMAN_BLOCKER

  blocking_findings: []
  spikes: []
  deferred: []

  planning_budget_status:
    plan_revisions:
    full_audits:
    subagents:
    wall_time:
    tokens:

  forbidden_actions:
    - launch_another_full_audit
    - expand_post_stage_scope

  reason:
```

---

# 5. Workstream B — Planning Budget

Planning 本身必须成为受约束资源。

扩展 Stage Contract：

```yaml
planning_budget:
  max_full_audits:
  max_plan_revisions:
  max_planning_subagents:
  soft_wall_fraction:
  max_planning_tokens: optional
  hard_stop:
```

推荐默认 heuristic：

```text
initial full audit <= 1
pre-execution full replan <= 1
普通 reviewer 不得递归 spawn reviewer
```

不要把具体数字写死为所有场景强制值；delivery profile / task size 可以覆盖。

---

# 6. Workstream C — Delivery Profile

Stage Contract 增加：

```yaml
delivery_profile:
  level: prototype | alpha | beta | rc | production
```

并为各 level 定义默认 assurance table。

至少区分：

## Alpha

默认必须：

```text
核心功能真实可运行
关键 fail-open/安全问题受控
focused tests
至少一个代表性 integration/E2E
```

默认不要求：

```text
完整 migration matrix
所有 edge cases
多轮 blind review
完整 crash matrix
rich UI polish
```

## RC / Production

才逐步提高：

```text
migration
compatibility
recovery
audit depth
full evidence
```

Plan-auditor 必须根据 delivery profile 判断 finding 是否阻塞。

---

# 7. Workstream D — Uncertainty Routing

第一版可作为 `planning-governor` 内部模块，不必单独做新 skill。

分类：

```yaml
uncertainty:
  type:
    ARCHITECTURE_DECISION
    REPOSITORY_FACT
    PUBLIC_SEAM_FEASIBILITY
    RUNTIME_FACT
    OPTIONAL_FEATURE
    EXTERNAL_BLOCKER
```

默认 route：

```text
ARCHITECTURE_DECISION → bounded reasoning / Human if semantic
REPOSITORY_FACT → bounded read
PUBLIC_SEAM_FEASIBILITY → spike
RUNTIME_FACT → spike/measurement
OPTIONAL_FEATURE → defer
EXTERNAL_BLOCKER → blocker
```

Hard rule：

> 如果一个问题可以在约 60–90 分钟内通过小型 executable test/spike 获得高置信答案，默认不得仅因“还不够确定”而继续追加 LLM reviewer。

---

# 8. Workstream E — Schedule Feasibility 修订

当前若存在：

```text
P80 > user target → mandatory replan
```

必须改掉。

新逻辑：

```text
1. initial forecast
2. if over target:
     at most one scope-fit pass
3. reforecast
4. if still over:
     output:
       likely checkpoint
       cut rules
       residual uncertainty
       expected range
5. 如果没有 EXECUTION_BLOCKER，允许进入 execution
```

Schedule 是：

> forecast

不是：

> 要求 planner 不断修改计划直到预测数字通过的 certification gate。

---

# 9. Workstream F — Planning Horizon Awareness

这是本版本第二个核心功能。

## 9.1 Project Contract 与 Stage Plan 分离

如果当前只有一个统一 Stage Contract，增加明确长期/短期 distinction。

### Project Contract

```yaml
project:
  objective:
  acceptance:
  hard_invariants:
  non_goals:
  frozen_decisions:
  delivery_profile:
  total_budget:
```

### Current Stage Plan

```yaml
stage:
  objective:
  assumes:
  guarantees:
  uncertainty_to_resolve:
  tasks:
  acceptance:
  budget:
  expected_information_gain:
  commitment_boundary:
  next_planning_trigger:
```

---

## 9.2 三 Horizon 输出

Planner 必须输出：

```yaml
horizons:
  commitment:
    tasks: []

  detailed_stage:
    objective:
    tasks: []

  forecast:
    stages:
      - objective:
        depends_on_evidence:
```

规则：

- commitment + detailed 可以有 leaf task；
- forecast 只能 Stage-level；
- forecast 不得产生大量提前 Task Package。

---

# 10. Workstream G — Stage Boundary Selector

新增一个明确 heuristic/procedure；可以并入 `stage-contract` 或 governor，不要求新 skill 数量膨胀。

Stage 应优先在以下位置结束：

```text
1. 将得到可能改变后续路线的新 evidence；
2. 高风险 assumption 将被验证；
3. shared seam 将被稳定冻结；
4. 一个独立可验证 capability 增量形成；
5. 后续所需 context cluster 明显改变；
6. 后续详细计划依赖尚未获得的执行结果；
7. 当前 Stage 已接近合理预算；
```

输出必须解释：

```yaml
stage_boundary:
  stop_after:
  because:
  expected_new_evidence:
  decisions_deferred_until_then:
```

Planner 必须能够明确说：

> “我只计划到这里。”

---

# 11. Workstream H — Next Planning Trigger

每个 Stage 必须包含：

```yaml
next_planning_trigger:
  normal:
    - stage_acceptance_reached

  early:
    - frozen_assumption_falsified
    - core_seam_blocker
    - route_changing_evidence
    - budget_envelope_threatened

  not_triggers:
    - first_worker_failure
    - optional_bug
    - mechanical_merge_conflict
```

这是未来 event-triggered runtime 的 schema hook。

本版本只生成和静态验证，不需要真正自动拉起 planner daemon。

---

# 12. Workstream I — Checkpoint / Drift / Recursive Plannability

升级现有 `checkpoint-handoff`。

## 12.1 Checkpoint

至少：

```yaml
checkpoint:
  achieved:
  verified_facts:
  verified_assumptions:
  falsified_assumptions:
  unresolved:
  exported_interfaces:
  tests:
  code_state:
  scope_deviations:
  budget_used:
  next_stage_inputs:
```

---

## 12.2 Drift Check

新增静态 transition checker：

```yaml
drift:
  requirements_removed:
  scope_added:
  frozen_decisions_changed:
  delivery_profile_changed:
  acceptance_changed:
  budget_envelope_changed:
```

注意：

```text
task reorder
route adjustment
spike insertion
```

不自动算 drift。

只有越出 Project Contract corridor 才算。

---

## 12.3 Recursive Plannability

Stage completion 必须能回答：

```text
stable checkpoint exists?
shared contracts consistent?
no hidden half-state?
next-stage inputs identifiable?
remaining Project acceptance still reachable?
```

第一版可以是 heuristic/rubric，不需要形式证明。

---

# 13. Workstream J — Workflow 与 Auditor 限权

`plan-auditor` 增加明确 `DO NOT AUDIT FOR`：

```text
future architecture completeness
deferred feature design
optional robustness outside delivery profile
speculative edge cases without concrete failure path
future Stage detailed DAG correctness
```

每个 finding 必须引用：

```text
具体 Stage acceptance
或
Project hard invariant
```

否则不能成为 EXECUTION_BLOCKER。

---

# 14. Eval 必须新增的 Regression Cases

至少加入：

## M — Meta-Planning Runaway

代表本次真实失败。

预期：

```text
<= one full audit before execution
empirical unknowns routed to spike
nonblocking findings deferred
planning budget enforced
time-to-first-evidence sharply reduced
```

## N — Too-Far Planning

未来 route 依赖尚未执行的 spike。

预期：

```text
current detailed plan ends at evidence boundary
future remains stage-level roadmap
```

## O — Premature Stage Split

两个任务共享上下文且中间没有信息增益。

预期：

```text
do not split only to satisfy arbitrary stage size
```

## P — Information-Gain Boundary

短 spike 决定两条后续路线。

预期：

```text
stage ends after spike
next-planning-trigger emitted
```

## Q — Cross-Stage Drift

下一 Stage 试图引入上层 non-goal。

预期：

```text
drift detected
```

---

# 15. Eval 指标升级

保留现有：

```text
completion
wall time
tokens
context
rework
integration defects
replans
compactions
```

新增：

```text
planning_wall_time
planning_tokens
planning_subagent_count
full_audit_count
plan_revision_count
time_to_first_executable_evidence
high_IQ_planner_calls (如果可观测)
future_plan_churn
stage_count
stage_drift_count
```

定义：

## Meta-Work Ratio

```text
planning + review + replan effort
/
effort before usable candidate
```

## Future Plan Churn

```text
提前详细规划、但在进入 commitment 前被删除/重写的 future work
/
提前详细规划的 future work
```

如果 current skills 比 baseline 生成更多“漂亮但随后作废”的远期 task，应被惩罚。

---

# 16. 现有 Evals 的重要保留项

不要为了减少 planning 而刷分。

必须继续防止：

```text
通过少读文件而漏必要上下文
通过少 task 制造巨型 leaf
通过不 review 漏真正 blocker
通过全部串行消除 ownership collision
通过全部 defer 逃避核心目标
```

因此新指标必须和：

```text
dependency correctness
scope discipline
integration explicitness
completion
security/correctness
```

一起解释。

---

# 17. 建议实现包

不要为每个 schema 字段单独起 Agent。

建议控制在约 6–8 个 implementation packages：

```text
P0 — current implementation map + regression fixture capture

A — Stage/Project schema + delivery profile + planning budget

B — Planning Governor + finding taxonomy + uncertainty routing

C — Auditor + risk/schedule behavior revision

D — Horizon/Stage-boundary/next-trigger logic

E — Checkpoint + drift + recursive-plannability extensions

F — Workflow/orchestrator integration

G — Eval fixtures/scorers/telemetry + end-to-end regression
```

可根据当前 repo ownership 合并。

---

# 18. Review 策略

开发本版本时不要再次重演规划 runaway。

每个 leaf：

```text
self-test
+
最多一个 focused reviewer（仅高风险时）
```

最终 integrated candidate：

```text
一个独立 focused review
+
eval comparison
```

除非出现真实 architecture blocker，不组织多轮 blind plan review。

---

# 19. 本版本 Definition of Done

只有以下全部满足，才算完成。

## Planning Governance

- [ ] planning budget 是一等字段；
- [ ] workflow 无无界 audit/replan loop；
- [ ] `EXECUTION_BLOCKER / SPIKE_REQUIRED / POST_STAGE / OPTIONAL` 可稳定输出；
- [ ] public seam/runtime uncertainty 能路由到 spike；
- [ ] delivery profile 影响 audit severity；
- [ ] schedule over-target 不再自动导致无限 replan。

## Horizon Awareness

- [ ] Project Contract 与 Current Stage Plan 分离；
- [ ] commitment / detailed / forecast 三 horizon 存在；
- [ ] future forecast 不展开 leaf DAG；
- [ ] Stage Plan 包含明确 stop boundary；
- [ ] 能输出“为什么只计划到这里”；
- [ ] `next_planning_trigger` 存在。

## Continuity

- [ ] Checkpoint 记录 verified/falsified assumptions；
- [ ] Drift checker 能发现 scope/acceptance/frozen decision 漂移；
- [ ] Stage completion 有 recursive-plannability 检查。

## Evals

- [ ] Case M–Q 至少有可运行 fixture；
- [ ] time-to-first-evidence / planning agent count / plan churn 有记录；
- [ ] 新版本相对现有版本在 runaway case 上显著改善；
- [ ] 不以明显降低 dependency/integration/correctness 为代价。

---

# 20. 成功后的下一步

本版本不要继续顺手实现下一阶段。

完成后输出：

```text
1. 新 workflow
2. 新 schemas
3. 修改/新增的 skills
4. Eval 前后对比
5. 当前仍依赖 prompt discipline 的地方
6. 哪些能力最值得下沉到 runtime/plugin state machine
```

然后停止。

下一阶段再单独设计：

> **Stagewise Receding-Horizon Runtime Compatibility**

重点才是：

```text
Project/Stage durable objects
state machine
planner invocation
Executive permissions
model routing
budget ledger
checkpoint store
dsh-agent-team integration
```

---

# 21. 最重要的实施原则

这次升级不要追求：

> “让 Planner 在执行前知道更多。”

要追求：

> **“让 Planner 知道什么时候已经知道得够多，可以开始执行；以及什么时候未来信息不足，因此应该明确停止详细规划并约定下一次 planning point。”**

这是 v1.1 的核心。
