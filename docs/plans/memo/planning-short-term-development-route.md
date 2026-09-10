# Planning Skills 短期开发路线
## 先解决 Planning Runaway 与“只计划到这里”的判断，再转架构兼容

**短期目标窗口**：1–2 轮 Skills 开发。  
**原则**：先改变 planning 行为，再改变运行时架构；先证明技能层能产生明显行为改善，再把状态/authority 下沉到 dsh-agent-team 等插件。

---

# 1. 短期目标

完成短期开发后，Planning Skills 应在大部分边界清楚的软件工程任务上具备两项稳定能力。

## 能力 A — Planning Behavior Control

能够避免：

```text
audit → replan → audit → replan
```

导致：

- reviewer/subagent 数失控；
- planning token 远高于 implementation；
- contract/Gate 不断增殖；
- alpha 被规划成 RC；
- 不确定性被持续文本审计，而不是 executable spike；
- 为满足噪声很大的 P80 估计而无限修改计划。

## 能力 B — Horizon Awareness

Planner 能明确判断：

> “我现在只应该计划到这里。”

并输出：

```text
当前 Detailed Stage 到哪里结束
为什么这里是信息边界
到达这里后会获得什么新证据
下一次 planning 应在什么 trigger 发生
未来内容只保留怎样的 roadmap
```

---

# 2. 短期架构原则

这 1–2 轮开发不追求完整 receding-horizon runtime。

只在 Skills 层建立最小抽象：

```text
Project Contract
      ↓
Planning Governor
      ↓
Current Stage Plan
      ↓
Execution / Spike
      ↓
Stage Checkpoint
      ↓
Next-Planning Trigger
```

先让单个 Planner 正确地产生这种结构。

插件状态机、durable Stage objects、自动 planner invocation、模型路由随后再做。

---

# 3. 第一轮：Planning Behavior Governance

建议版本：

> **v1.1-A — Planning Governance Patch**

预计这是最重要的一轮。

## 3.1 新增 `planning-governor`

这是新的核心 Skill。

职责：

```text
控制 planning budget
控制 reviewer budget
控制 replan 次数
决定是否允许继续 planning
把 uncertainty 路由到 read / reason / spike / defer / human
阻止普通 finding 触发全局 REPLAN
执行 delivery-profile 约束
```

推荐输出：

```yaml
planning_governor:
  status: EXECUTE | SPIKE | TARGETED_PATCH | HUMAN_BLOCKER

  planning_budget:
    used:
    remaining:

  findings:
    execution_blocker: []
    spike_required: []
    post_stage: []
    optional: []

  allowed_next_actions: []

  forbidden_next_actions: []

  stop_reason:
```

---

## 3.2 修改 `stage-contract`

新增：

```yaml
delivery_profile:
  level: prototype | alpha | beta | rc | production

planning_budget:
  max_full_audits:
  max_plan_revisions:
  max_planning_subagents:
  soft_wall_fraction:
  hard_stop_condition:

scope_priority:
  must:
  should:
  deferable:
```

目的：

- 防止 alpha 被审成 production；
- 防止 reviewer 把 SHOULD 变 MUST；
- 让 planning 自身也成为受预算约束的资源。

---

## 3.3 修改 `plan-auditor`

当前 `BLOCKER / MAJOR / MINOR` 应升级为行动分类：

```text
EXECUTION_BLOCKER
SPIKE_REQUIRED
POST_STAGE
OPTIONAL
```

每个 finding 必须回答：

```text
1. 如果不处理，本 Stage 的哪条 acceptance 会失败？
2. 是否有具体 failure path？
3. 是否可以通过 ≤约 60–90 min executable probe 得到答案？
4. 是否属于 delivery profile 要求？
```

若无法指向 Stage acceptance 或 hard invariant：

```text
默认 POST_STAGE / OPTIONAL
```

---

## 3.4 新增 uncertainty routing

第一版可以并入 `planning-governor`，不要急着拆成新 skill。

分类：

```text
A Architecture decision
B Repository fact
C Public seam feasibility
D Runtime/performance fact
E Optional feature uncertainty
F True external blocker
```

默认动作：

| 类型 | 默认 |
|---|---|
| A | bounded planning / Human if product semantic |
| B | bounded read |
| C | implementation spike |
| D | measurement/spike |
| E | defer |
| F | blocker |

硬规则：

> 能通过短时 executable evidence 得到答案的问题，不允许因“需要更高信心”而无限追加 reviewer。

---

## 3.5 修改 schedule estimation

从：

```text
P80 > target
→ mandatory replan
```

改成：

```text
initial forecast
→ at most one scope-fit pass
→ reforecast
→ still over:
   report likely checkpoint + cut rules + residual uncertainty
   start execution when no blocker
```

Schedule 是 forecast，不是 formal certification。

---

## 3.6 修改总控 workflow

旧：

```text
plan
→ audit
→ revision
→ audit
→ ...
→ execution
```

新：

```text
Stage Contract
→ Plan
→ one Audit
→ Planning Governor
     ├ EXECUTE
     ├ SPIKE
     ├ TARGETED_PATCH
     └ HUMAN_BLOCKER
```

禁止 `audit → audit` 的直接回边。

---

# 4. 第一轮 Eval：把这次失败保存成 Regression Case

新增：

> **Case M — Meta-Planning Runaway**

Fixture 特征：

```text
成熟仓库
已有大量 backend primitives
3–4 个真实但局部的不确定 seam
用户要求短时间 alpha
reviewer 每轮都能发现合理但非致命问题
```

错误轨迹：

```text
audit
→ REPLAN
→ fresh audit
→ new contract
→ schedule grows
→ scope shrinks
→ more audit
→ no implementation
```

预期新行为：

```text
one plan
→ one audit
→ findings classified
→ empirical unknowns become spikes
→ optional findings deferred
→ blocker patched once
→ execution begins
```

必须新增指标：

```text
planning_subagent_count
planning_tokens
planning_wall_time
plan_revision_count
full_audit_count
time_to_first_executable_evidence
meta_work_ratio
```

---

# 5. 第一轮完成标准

第一轮通过后，应满足：

1. Planning workflow 不存在无界 audit/replan loop；
2. planning budget 是 Stage Contract 的一等字段；
3. auditor finding 可以程序化区分 blocker/spike/defer；
4. schedule overrun 不自动制造无限 REPLAN；
5. Case M 在重复运行中显著减少：
   - planner/reviewer agent 数；
   - planning token；
   - time-to-first-evidence；
6. 不明显降低已有：
   - dependency correctness；
   - ownership collision detection；
   - integration explicitness；
   - scope discipline。

如果第一轮已经让真实 Planning Skills 在代表性任务上稳定停止 planning，可进入第二轮。

---

# 6. 第二轮：Planning Horizon / Stage Boundary

建议版本：

> **v1.1-B — Horizon Awareness MVP**

核心问题：

> Planner 怎样判断“我现在只计划到这里”？

---

## 6.1 Project Contract 与 Stage Plan 分离

Project Contract：

```yaml
objective:
acceptance:
hard_invariants:
non_goals:
delivery_profile:
frozen_decisions:
budget_envelope:
```

Stage Plan：

```yaml
stage_id:
objective:
assumes:
guarantees:
entry_checkpoint:
uncertainty_to_resolve:
tasks:
acceptance:
budget:
expected_information_gain:
commitment_boundary:
next_planning_trigger:
future_roadmap:
```

---

## 6.2 三 Horizon

必须显式输出：

```yaml
horizons:
  commitment:
  detailed_stage:
  forecast:
```

### Commitment
正在/即将执行，不允许普通 replanning 改写。

### Detailed
当前 Stage 的完整任务 DAG。

### Forecast
未来只保留 Stage-level roadmap。

---

## 6.3 Stage Boundary Selector

加入判断原则：

Stage 应在满足以下一个或多个条件的位置结束：

```text
1. 将获得可能改变后续路线的新证据；
2. 高风险 assumption 将被验证/证伪；
3. 一个稳定 shared seam 将形成；
4. 一个完整可验证 capability 增量将形成；
5. 后续工作所需上下文将发生明显切换；
6. 继续详细规划将高度依赖尚未获得的执行结果；
7. 当前 Stage 已接近 planning/execution budget 上限。
```

反例：

```text
仅因为文档章节结束
仅因为四小时到了
仅因为一个模块开发完
```

---

## 6.4 `next_planning_trigger`

每个 Stage 必须输出：

```yaml
next_planning_trigger:
  normal:
    - stage_acceptance_reached

  early:
    - frozen_assumption_falsified
    - core_seam_blocker
    - budget_deviation
    - route_changing_evidence

  not_triggers:
    - first_worker_failure
    - optional_bug
    - mechanical_conflict
```

---

## 6.5 Stage Checkpoint

升级 `checkpoint-handoff`。

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
  project_contract_delta:
  next_stage_inputs:
```

下一轮 planner 应优先消费：

```text
Project Contract
+
Previous Stage Contract
+
Stage Checkpoint
+
必要局部 code evidence
```

而不是全部历史对话。

---

## 6.6 Drift Detector MVP

第二轮先不做复杂状态机。

只做 Stage transition 静态检查：

```yaml
drift:
  requirements_removed:
  scope_added:
  frozen_decisions_changed:
  delivery_profile_changed:
  acceptance_changed:
  budget_envelope_changed:
```

正常应为空或具有 Human/Project-level authorization。

注意：

> task reorder / local route change 不自动算 drift。

---

## 6.7 Recursive Plannability Check

Stage acceptance 增加：

```text
是否留下稳定 checkpoint？
是否没有 half-applied shared state？
是否能明确下一阶段输入？
remaining Project acceptance 是否仍可达？
```

这比要求完整未来 DAG 更重要。

---

# 7. 第二轮 Eval

至少增加四类 case。

## Case N — Too-Far Planning

未来关键 seam 尚未验证。

期望：

```text
只详细规划到 seam evidence；
未来只留 roadmap。
```

## Case O — Premature Stage Boundary

两个任务共享同一上下文且中间没有新信息。

期望：

```text
不要无意义拆 Stage。
```

## Case P — Information-Gain Boundary

一个 45min spike 会决定两条后续路线。

期望：

```text
Stage 在 spike 后结束并触发 next plan。
```

## Case Q — Drift Across Stages

前一 Stage non-goal 在下一轮被偷偷加入。

期望：

```text
Drift Detector 拒绝。
```

---

# 8. 短期完成标准

完成 1–2 轮后，Planning Skills 应在大部分普通软件工程长任务上表现为：

```text
不会无限规划
不会无限审计
知道什么时候 executable spike 更值钱
不会把 alpha 审成 RC
能够输出一个有限当前 Stage
能够明确说：
“我只计划到这里；
完成 X / 获得 Y 证据后重新规划。”
未来工作保持 Stage-level roadmap
跨 Stage 不丢 Project acceptance / non-goals / hard constraints
```

此时已经足够转入下一阶段：

> **架构兼容 / runtime integration。**

---

# 9. 之后再做：架构兼容与插件化

短期能力验证后，再设计：

```text
Project / Stage / Task durable objects
state machine
planner invocation service
worker lifecycle
budget ledger
model routing
authority
checkpoint store
event-trigger evaluator
```

并考虑接入：

```text
dsh-agent-team
deepseek-harness plugin
其他 Agent runtime
```

原则：

> 先让 Skills 证明控制策略有效，再把策略变成 runtime enforcement。

不要反过来先建复杂状态机，然后再猜其 planning policy 是否有效。

---

# 10. 不应在短期混入的内容

明确 defer：

```text
learned planner invocation policy
automatic Value-of-Computation estimator
Monte Carlo adaptive horizon
multi-planner consensus
complex planner ensemble
global knowledge graph
fully autonomous Human-free project governor
automatic model marketplace routing
formal verification of recursive plannability
large plugin UI
```

这些属于后续研究/工程阶段。

---

# 11. 推荐短期版本命名

```text
v1.1-A
Planning Governance Patch

v1.1-B
Horizon Awareness MVP

v1.2
Stagewise Receding-Horizon Workflow

v1.3
Runtime / dsh-agent-team Compatibility

v2
Hierarchical Receding-Horizon Agent Control
```

如果两轮合并，也可直接称：

> **v1.1 — Planning Governance & Horizon Awareness**

---

# 12. 短期最关键的成功信号

升级后的 Planning Skills 不需要一开始生成更聪明、更长的计划。

最重要的行为变化应该是：

```text
更少的 planner/reviewer 调用
更少的 planning token
更快获得 executable evidence
更少计划未来尚无证据支撑的细节
明确声明 planning horizon
到达 horizon 后有结构化 checkpoint
下一轮 planning 不需要重新考古
```

如果这几项出现，短期路线就是成功的。
