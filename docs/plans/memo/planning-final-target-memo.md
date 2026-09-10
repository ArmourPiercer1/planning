# 最终目标备忘
## 从 Planning Skills 到“一句话实现……”的长任务 Agent 监督控制系统

**状态**：长期方向备忘，不作为当前版本一次性实现范围。  
**目标用户体验**：在目标定义良好、约束可表达、仓库/工具接口可访问的情况下，用户可以用接近“一句话实现……”的方式启动一个长时间工程任务；系统自行完成分阶段规划、执行、验证、重规划和交付，同时保持目标、架构约束、预算与质量标准不漂移。

---

# 1. 最终愿景

目标不是构造一个“更会写计划的 LLM”。

目标是构造：

> **一个面向长时间 Agent 工作流的 supervisory control system。**

用户输入：

```text
“在不修改 DSH core 的前提下，把 dsh-agent-team 的 capability policy
真正接到 live Agent，并给文件工具加入安全的参数权限控制；
先交付一个可用 alpha，完整动态治理后续迭代。”
```

系统应能够自动：

```text
理解目标与约束
→ 建立长期 Project Contract
→ 选择第一个信息/风险最有价值的 Stage
→ 调度执行 Agent
→ 收集代码、测试和运行时证据
→ 判断是否需要再次调用高智力 Planner
→ 生成下一 Stage
→ 继续执行
→ 集成
→ 验证
→ 输出 usable candidate
```

用户不需要持续手工：

```text
追问进度
纠正 scope
要求别再拉 reviewer
手动决定什么时候 replan
重新向新 Agent 解释历史
```

---

# 2. 核心范式

系统采用：

> **Contract-Constrained, Event-Triggered, Receding-Horizon Execution**

而不是：

> upfront full-plan → long-horizon execution。

抽象：

```text
Human Goal
   ↓
Project Governor / Project Contract
   ↓
High-IQ Strategic Planner   ←──────────────┐
   ↓                                       │
Stage Proposal                             │
   ↓                                       │
Planning Governor                          │
   ↓ admitted Stage                        │
Cheap Executive / State Machine            │
   ↓                                       │
Workers / Integrators / Testers            │
   ↓                                       │
Executable Evidence                        │
   ↓                                       │
Stage Checkpoint ── trigger? ──────────────┘
```

---

# 3. 五层长期架构

## Layer 0 — Human / Project Governor

职责：

- 定义最终目标；
- 定义不可突破的约束；
- 定义 delivery profile；
- 定义总预算；
- 裁决真正需要修改长期目标的冲突。

长期目标是降低 Human 介入频率，而不是完全取消 Human authority。

---

## Layer 1 — Project Contract

系统的长期“状态走廊”。

至少包含：

```yaml
project:
  objective:
  acceptance:
  hard_invariants:
  explicit_non_goals:
  delivery_profile:
  frozen_decisions:
  budget_envelope:
  allowed_scope_changes:
  human_escalation_conditions:
```

Project Contract 不是长期详细计划。

它只定义：

> 什么算成功，以及哪些东西不能为了局部便利而改变。

---

## Layer 2 — High-IQ Strategic Planner

昂贵、低频、事件触发。

它不承担持续 orchestration。

职责：

- 理解当前 Checkpoint；
- 识别当前最有价值的下一阶段；
- 处理真正架构不确定性；
- 选择 Stage horizon；
- 选择 spike / implementation / integration / verification；
- 给出 Stage acceptance、fallback 和下次 planning trigger。

Planner 不应：

- 持续轮询 worker；
- 为每个 leaf 重新读全仓；
- 管理普通 retry；
- 为非阻塞 bug重做总体计划。

---

## Layer 3 — Planning Governor

确定性或低智能、高指令遵循。

职责：

- 校验 Stage Proposal 是否违反 Project Contract；
- 控制 Stage 大小；
- 控制 planning/reviewer/replan budget；
- 防止 alpha 变 RC；
- 防止未来 feature 渗入当前 critical path；
- 对 uncertainty 进行 route：plan / read / spike / defer / human；
- 决定 Planner 是否真的应该被再次调用。

长期可以由 dsh-agent-team/plugin 状态机提供强约束，而不是只依赖 prompt。

---

## Layer 4 — Cheap Executive

持续运行，但不拥有战略规划 authority。

职责：

```text
DAG state
READY 判断
dispatch
worker budget
retry policy
task result ingestion
checkpoint
integration scheduling
test scheduling
planner-trigger detection
```

它应优先选择：

> 较弱、便宜、速度快、指令遵循稳定的模型。

Executive 不允许：

```text
自行改变 Project Contract
自行重开冻结架构
自行扩大 Stage
为普通失败无限追加任务
```

---

## Layer 5 — Workers / Integrators / Reviewers

按局部 context 工作。

不同任务可路由不同模型：

- 机械实现：弱模型；
- 高局部推理：中模型；
- 架构异常：强模型；
- focused review：按风险调用；
- candidate security review：独立强 reviewer。

Worker 的主要输入不是完整项目历史，而是：

```text
Task Package
+
Frozen Contract
+
Required Context
+
Current code state
```

---

# 4. 三个 Planning Horizon

最终系统必须显式区分：

## Commitment Horizon

已经 dispatch / 正在执行的近端工作。

修改成本高，不允许普通 Planner 静默改写。

## Detailed Stage Horizon

当前详细计划。

只有这里需要 leaf DAG、ownership、acceptance、budget。

## Forecast Horizon

未来 roadmap。

只保存：

- stage objective；
- dependencies on future evidence；
- risks；
- options；
- rough budget。

不提前生成详细任务。

---

# 5. 长期稳定性的核心：Recursive Plannability

最终系统不追求：

> “一开始知道所有未来步骤。”

它追求：

> “每一步之后都仍然处于一个可以安全继续规划的状态。”

每个 Stage 必须满足：

```text
stable checkpoint
verified guarantees
no hidden architecture drift
no half-applied shared state
next-stage inputs known
remaining project objective still reachable
```

这称为：

> **Recursive Plannability**

它应成为整个系统最重要的 correctness invariant 之一。

---

# 6. Drift 的最终定义

长期系统不能把任何偏离原计划都视为 drift。

真正需要控制的是：

## Requirement Drift
最终 acceptance 被静默删除/弱化。

## Scope Drift
未来 feature、技术债、顺手重构被吸收。

## Architecture Drift
冻结架构被低层 Agent 改写。

## Assurance Drift
delivery profile 被改变，例如 alpha 被规划成 RC。

## Budget Drift
规划、review 或 execution 持续膨胀但没有提升当前目标可达性。

## Authority Drift
Executive / Worker 获得了本不应拥有的重新规划或长期目标修改能力。

局部 task 顺序变化不是 drift，只要仍处于 Project Contract corridor。

---

# 7. “一句话实现”的必要前提

远期系统不应声称任何任务都可以“一句话实现”。

它适用于：

```text
目标相对明确
acceptance 可表达
repo/tool 可访问
修改范围可被状态机约束
运行测试可自动执行
Human 可在真正高层冲突时介入
```

最理想的任务：

- 软件功能开发；
- repo 清理/重构；
- migration；
- agent/plugin 开发；
- 测试体系补齐；
- 多阶段 research→implementation 工程任务。

不适合完全无人监督的情形：

- 目标本身高度政治/组织性；
- acceptance 依赖主观审美且无法代理；
- 外部系统不可测试；
- 高风险 irreversible action 无法 sandbox；
- Human intent 尚未稳定。

---

# 8. 与 dsh-agent-team 等插件的远期融合

Planning Skills 初期可以是 prompt/skill 层。

长期应把关键状态与 authority 下沉到插件。

建议未来状态机对象：

```text
Project
  ↓
Stage
  ↓
Workstream
  ↓
Task
```

每个对象具备：

```text
state
owner
budget
contract
dependencies
checkpoint
evidence
authority
```

插件可以提供：

- 状态机；
- durable checkpoint；
- worker lifecycle；
- model routing；
- planner invocation；
- budgets；
- review quotas；
- task isolation；
- branch/worktree ownership；
- human control surface；
- long-running resume。

这会让 Planning Skills 从“prompt discipline”升级成真正的运行时控制系统。

---

# 9. 长期模型分工原则

最终系统不默认：

> “最强模型做 Main Agent。”

而采用：

```text
cheap deterministic model
→ 高频 executive work

task-matched worker models
→ 实现工作

high-IQ planner
→ 低频战略推理

high-IQ reviewer
→ 真正高风险 gate
```

长期要优化的不是单模型能力，而是：

> **Intelligence Allocation**

即在什么时候花更昂贵的 reasoning 最值得。

---

# 10. 长期优化目标

可以抽象为：

\[
\min
\left(
T_{\mathrm{wall}},
C_{\mathrm{token}},
C_{\mathrm{model}},
C_{\mathrm{rework}},
R_{\mathrm{failure}}
\right)
\]

subject to：

\[
\text{Project Contract}
\]

并同时最大化：

```text
completion probability
local recoverability
checkpoint sufficiency
recursive plannability
human steering efficiency
```

---

# 11. 核心长期指标

除完成率外，至少应持续测量：

```text
time_to_first_executable_evidence
planning_wall_time
planning_tokens
planning_subagents
high_IQ_planner_invocations
reviewer_invocations
plan_revision_count
stage_count
stage_drift_rate
scope_creep
integration_rework
checkpoint_context_reduction
worker_context_amplification
human_interventions
total_wall_time
```

尤其关注：

## Meta-Work Ratio

```text
(planning + reviewing + replanning)
/
total effort before usable candidate
```

## Planning Waste

提前规划但在真正进入 commitment 前被废弃/重写的未来计划比例。

## Checkpoint Sufficiency

下一轮 planner 能否主要依赖：

```text
Project Contract + Checkpoint + local code evidence
```

而不是重新考古整个任务历史。

---

# 12. 版本演进愿景

## v1.0 — Long-Task Planning Compiler

解决：

> 怎样把大任务拆成 context-bounded execution DAG。

## v1.1 — Planning Behavior Control + Horizon Awareness

解决：

> 怎样防止 planning 自己失控；怎样知道“只计划到这里”。

## v1.2 — Stagewise Receding-Horizon Planning

解决：

> 怎样稳定执行 Stage → Checkpoint → Next Stage，而不发生 drift。

## v1.3 — Runtime/Plugin Compatibility

把 Project/Stage/Task state、budget、trigger、authority 对接插件状态机。

## v1.x — Resource-Aware Planning

加入：

- planner value-of-computation；
- adaptive Stage horizon；
- model routing；
- learned planner trigger；
- historical performance profile。

## v2.0 — Hierarchical Receding-Horizon Agent Control

形成完整：

```text
Human
→ Project Governor
→ Strategic Planner
→ Planning Governor
→ Executive
→ Workers
→ Evidence
→ Checkpoint
→ Event-triggered replanning
```

---

# 13. 远期成功标准

最终目标不是：

> “计划文档看起来非常完备。”

而是：

> 用户给出一句目标和少量关键约束后，系统能够长时间自主推进；执行过程中只在真正值得重新思考时调用高智力 planner；局部失败可恢复；未来计划按证据逐步展开；项目长期 acceptance、架构约束和预算不漂移；最终交付可验证的成品。

这才是“一句话实现……”体系的合理含义。
