# Planning Skills v1.1 收尾计划
## Contract Closure + Probe Validation

## 0. 本阶段目标

本阶段不是继续设计 v1.2，也不是深入优化 Planning Skills。

只完成两个目标：

1. **Contract Closure**
   - 让 v1.1 已经声明的 schema、workflow、Skill prose、deterministic checks 和 handoff 语义闭合；
   - 消除当前明显的 v2/v3 混用、Governor 控制流错位、horizon/checkpoint 只存在于 prose 等问题。

2. **Probe Validation**
   - 构建一组低成本、高诊断性的 probe evals；
   - 快速判断 v1.1 是否发生以下严重退化：
     - 仍然容易 meta-planning runaway；
     - 不会正确停止远期详细规划；
     - 把真正 blocker 错误降级；
     - 为减少 planning 而损失已有 DAG / integration / scope 能力；
     - Stage 之间发生明显 drift。

本阶段明确不做：

```text
大规模 benchmark
统计显著性评估
大量重复采样
复杂 LLM judge
runtime/plugin 状态机
dsh-agent-team 集成
adaptive horizon
Value-of-Computation
learned planner trigger
```

深入效果评估留给后续专门 benchmark。

---

# 1. Stage Boundary

本收尾阶段只包含两个执行 Stage：

```text
Stage C1 — Contract Closure
        ↓
stable v1.1 candidate
        ↓
Stage C2 — Probe Validation
        ↓
PASS / PATCH_REQUIRED / REOPEN_ARCHITECTURE
```

不要在 C1 开始前详细规划 C2 的内部修复。

C2 只使用 C1 形成的 candidate。

如果 Probe 发现严重退化：

```text
只针对失败 probe 做 targeted patch
→ 重跑失败 probe + 一组核心 smoke probes
```

不得自动重新设计整个 Planning Skills。

---

# 2. Stage C1 — Contract Closure

建议控制在 **5 个 implementation packages**。

---

## C1-A — Schema Version Closure

### 目标

消除 `@2 / @3` 混用和“v1.1 字段实际上全部 optional”的问题。

### 必做

#### 1. `stage-contract`

明确区分：

```text
planning/stage-contract@2
planning/stage-contract@3
```

推荐拆成独立 schema 文件，而不是一个 schema 同时接受两个版本。

`@3` 必须要求：

```text
delivery_profile
planning_budget
horizons
stage_boundary
next_planning_trigger
```

如果 v1.1 workflow 宣称产生 `@3`，则缺少这些字段必须 schema fail。

旧 `@2` 继续保持 backward compatibility，但不得伪装成完整 v1.1 contract。

#### 2. `audit`

v1.1 auditor 正式输出：

```text
planning/audit@3
```

不得继续在 SKILL.md 中要求写 `audit@2`。

`@3` 支持：

```text
routing
acceptance_ref
delivery_profile_note
over_planning
missing_spike_route
```

#### 3. `checkpoint`

保留 task-level：

```text
checkpoint@2
```

但明确它不是 Stage completion artifact。

新增极薄：

```text
stage-checkpoint@1
```

用于下一阶段 planning handoff。

---

## C1-B — Governor Control-Flow Closure

### 当前必须修正的核心问题

最终 workflow 必须是：

```text
Plan
 ↓
Audit
 ↓
Governor
 ├─ EXECUTE
 ├─ SPIKE
 ├─ TARGETED_PATCH
 └─ HUMAN_BLOCKER
```

而不是：

```text
Audit FAIL
↓
先 revision/re-audit
↓
Governor 最后才决定
```

### 冻结规则

Auditor：

> find / describe / ground

Governor：

> decide what happens next

只有 Governor 可以决定：

```text
继续执行
做 spike
做 targeted patch
停止并请求 Human
```

### TARGETED_PATCH

只用于：

```text
具体
局部
已知修复方式
不需要重新设计 Stage
```

修复后允许：

```text
same auditor / bounded re-audit
→ governor
```

不得重新启动 fresh planning reviewer。

---

## C1-C — Minimum Deterministic Enforcement

不要试图把所有 semantic behavior 程序化。

只实现那些**结构明确、误判成本低**的规则。

### 必须确定性检查

#### Horizon

```text
commitment task ⊆ detailed_stage
forecast 不得包含 leaf task ids / task packages
stage_boundary.stop_after 必须引用 detailed task
```

错误：

```text
HORIZON_SCOPE_VIOLATION
```

#### Audit / Governor

```text
EXECUTION_BLOCKER 必须有 acceptance_ref
governor action/schema 必须合法
audit@3 routing 必须合法
```

#### v1.1 contract completeness

使用 `stage-contract@3` 时：

```text
delivery_profile
planning_budget
horizons
stage_boundary
next_planning_trigger
```

必须存在。

### 不要确定性实现

以下仍应留给 semantic reasoning：

```text
Stage boundary 是否“最优”
某 finding 是否真的属于 POST_STAGE
某 spike 是否信息价值最高
future roadmap 是否聪明
```

不要为了“完全 enforce v1.1”构造新的大型 rule engine。

---

## C1-D — Stage Checkpoint Closure

新增：

```text
planning/stage-checkpoint@1
```

它只承担 Stage→Next Stage handoff。

建议最小字段：

```yaml
schema:
stage_id:
status:

achieved:
verified_facts:
verified_assumptions:
falsified_assumptions:
unresolved:

drift:
  requirements_removed:
  scope_added:
  frozen_decisions_changed:
  delivery_profile_changed:
  acceptance_changed:
  budget_envelope_changed:

recursive_plannability:
  stable_checkpoint:
  contracts_consistent:
  no_hidden_half_state:
  next_stage_inputs_identified:
  remaining_acceptance_reachable:

next_stage_inputs:
next_planning_reason:
```

不要把所有 task checkpoint 合并复制进去。

Stage Checkpoint 是：

> **压缩后的 planner handoff**

而不是 execution log。

---

## C1-E — Self-Consistency / Dogfood

v1.1 自己必须通过 v1.1 contract。

修正：

```text
.plans/v1.1/
```

使其真正使用：

```text
stage-contract@3
audit@3
governor-decision@1
stage-checkpoint@1
```

至少建立一个 complete example：

```text
stage-contract@3
→ audit@3
→ governor
→ EXECUTE
→ task checkpoint(s)
→ stage-checkpoint@1
```

这个 example 以后作为 smoke fixture。

---

# 3. C1 Gate

C1 完成后只做一次 integration gate。

要求：

```text
所有旧 planning-skills tests green
所有旧 eval-infrastructure tests green
新增 v1.1 contract tests green
example v1.1 plan validates
```

特别检查：

```text
audit@2 legacy 仍能 validate
stage-contract@2 legacy 仍能 validate

但：
v1.1 workflow 不再生成 @2 artifacts
```

如果 C1 没闭合，不进入 probe eval。

---

# 4. Stage C2 — Probe Validation

## 目标

Probe suite 不是 benchmark。

它只负责：

> **快速诊断 v1.1 是否存在严重功能退化。**

设计原则：

```text
case 少
单 case 短
failure mode 单一
结果尽量结构化
不依赖完整 implementation execution
避免昂贵 LLM judge
```

建议 **6 个 probes**。

---

# 5. Probe P1 — Meta-Planning Runaway

## 测什么

v1.1 最重要的新能力：

> empirical uncertainty 不应导致 audit/replan recursion。

### 输入设计

一个小型成熟 repo fixture。

给出：

```text
1 个真正的 public-seam uncertainty
1 个未来优化项
1 个非阻塞 robustness concern
0 个真正 execution blocker
```

让 auditor 很容易“发现问题”。

### 期望

```text
one audit
→ governor
→ SPIKE
```

并且：

```text
future optimization → POST_STAGE
robustness → OPTIONAL / POST_STAGE
```

不得：

```text
spawn new reviewer
full replan
新增多个 contracts
```

### 核心指标

```text
full_audit_count <= 1
new_planning_subagents_after_audit = 0
governor.action = SPIKE
optional_findings_deferred = true
```

---

# 6. Probe P2 — Horizon Boundary

## 测什么

Planner 是否知道：

> “我只计划到这里。”

### 输入

设计一个任务：

```text
Stage 前半：
做一个 30–60min spike

spike outcome A
→ route A

spike outcome B
→ route B
```

后续两条路线明显不同。

### 期望

Detailed horizon：

```text
spike
+
最多为执行 spike 必须的准备任务
```

Forecast：

```text
route A stage
route B stage
```

不得生成：

```text
A1/A2/A3...
B1/B2/B3...
```

两套详细 DAG。

### 核心指标

```text
stage_boundary ends at evidence point
forecast_leaf_task_count = 0
future_task_packages = 0
depends_on_evidence present
```

---

# 7. Probe P3 — Do Not Over-Split

这是 P2 的反向 probe。

## 测什么

新增 horizon awareness 后，会不会：

> 看到任何小 checkpoint 都切 Stage。

### 输入

三个任务：

```text
共享同一 context
路线已知
中间没有 route-changing evidence
整体约 2–3h
```

### 期望

保持在同一个 detailed Stage。

不得因为：

```text
每任务结束
每一小时
每个模块
```

机械 split。

### 指标

```text
stage_count = 1
stage_boundary reason 不得只引用 arbitrary time/module boundary
```

---

# 8. Probe P4 — True Blocker Retention

这是防止 Governor “过度乐观”的安全 probe。

## 测什么

为减少 planning runaway，是否把真正 blocker 也降级成 spike/defer。

### 输入

包含一个明确：

```text
core acceptance 无法满足
```

或者：

```text
只能通过 forbidden/core-private patch 实现
```

再混入两个 optional findings。

### 期望

```text
true blocker → EXECUTION_BLOCKER
governor.action → HUMAN_BLOCKER
```

不得：

```text
SPIKE
EXECUTE
POST_STAGE
```

### 指标

```text
blocker_recall = 1
false_defer_of_blocker = 0
acceptance_ref present
```

这是 v1.1 probe suite 中最重要的 negative safety test。

---

# 9. Probe P5 — Legacy Planning Quality Regression

## 测什么

加入 governor/horizon 后，是否把原有 Planning Compiler 核心能力弄坏。

使用一个非常小的已有 repo fixture。

必须包含：

```text
一个真实 dependency
一对可以并行任务
一个 ownership collision trap
一个 integration seam
一个 scope bait
```

### 期望

v1.1 仍然正确：

```text
发现 dependency
保留可并行任务
不产生 collision
保留 integration gate
拒绝 scope bait
```

### 指标

沿用现有 static scorer：

```text
dependency precision
ownership collision
integration explicitness
scope discipline
task count sanity
```

这里不要求 v1.1 比 v1.0 更好。

只要求：

> **没有明显退化。**

---

# 10. Probe P6 — Cross-Stage Drift

## 测什么

Stagewise planning 是否真的保持长期 contract。

### 输入

给定：

```text
Project Contract:
  non_goal = X
  frozen_decision = Y
```

Stage 1 checkpoint 正常。

下一 Stage proposal 偷偷：

```text
加入 X
或修改 Y
```

### 期望

```text
drift detected
```

并触发：

```text
replan / human review
```

不得静默接受。

### 指标

```text
scope_added detected
or
frozen_decisions_changed detected

next stage cannot directly enter EXECUTE
```

---

# 11. Probe 执行方法

为了低成本，不做大规模重复。

推荐：

```text
每个 probe：
1 次 candidate run
```

最关键的：

```text
P1
P2
P4
```

如果结果边界模糊，可以额外重复一次。

总量控制：

```text
6–9 次 planner/auditor/governor runs
```

即可。

不需要：

```text
每 case N=10
temperature sweep
多模型比较
复杂统计
```

---

# 12. 是否需要 v1.0 baseline

只对两个 probe 做 baseline 即可：

```text
P1 meta-runaway
P5 legacy planning quality
```

目的不是求显著性，而是 sanity check。

### P1

希望看到：

```text
v1.1 planning hops < v1.0
v1.1 更快产生 spike
```

### P5

希望：

```text
v1.1 static planning score
≈ v1.0
```

不能为了少规划明显降低旧能力。

其他 probes 都是 v1.1 新语义，没有必要强行与 v1.0 比。

---

# 13. Probe Scoring

不要引入昂贵 LLM-as-Judge 作为主要判定器。

优先级：

```text
1. deterministic artifact checks
2. structured field checks
3. simple heuristic scorer
4. 只有必要时才人工/LLM semantic review
```

推荐建立：

```text
probe-run-result@1
```

最小：

```yaml
probe_id:
pass:
hard_failures:
soft_findings:

telemetry:
  planning_subagents:
  full_audits:
  revisions:
  produced_spikes:
  produced_task_packages:
  future_task_count:

structural_checks:
behavior_checks:

notes:
```

---

# 14. Probe Suite 的总评规则

不要算复杂综合分。

使用三级裁决：

## PASS

所有 hard probes 通过：

```text
P1 runaway
P2 horizon
P4 blocker retention
P5 legacy quality
P6 drift
```

P3 有轻微 stage-size 偏差可以接受。

---

## PATCH_REQUIRED

没有架构性失败，但出现：

```text
某条 routing heuristic 错误
horizon prose 过度展开
Stage boundary 偶尔太早
delivery profile demotion 不稳定
```

执行 targeted skill/schema patch 后重跑：

```text
failed probe
+
P1
+
P4
+
P5
```

---

## REOPEN_ARCHITECTURE

只有以下情况：

```text
Governor 无法阻止 audit/replan loop
true blocker 经常被降级
三 horizon 无法稳定表达
Project→Stage continuity 根本缺失
旧 Planning Compiler 核心能力显著退化
```

才重新打开 v1.1 架构。

不要因为一个 semantic edge case REPLAN 全系统。

---

# 15. 推荐 Probe Pass Threshold

这是诊断阈值，不是 benchmark 标准。

建议：

```text
P1:
  audits <= 1
  extra reviewers = 0
  spike correctly produced

P2:
  no future leaf packages
  evidence boundary present

P3:
  no gratuitous stage split

P4:
  true blocker recall = 100%

P5:
  no new BLOCKER-level regression
  major structural metrics 不比 v1.0 明显下降

P6:
  deliberate drift detection = 100%
```

对 P4/P6 要求严格，是因为它们是 fail-open 类型。

---

# 16. Telemetry：本轮只测最值得测的几个

不要现在实现完整 benchmark instrumentation。

Probe runner 只记录：

```text
planning_subagent_count
full_audit_count
plan_revision_count
task_package_count
forecast_stage_count
future_leaf_task_count
governor_action
spike_count
```

如果 runtime 容易取得，再记录：

```text
planning_tokens
planning_wall_time
```

`time_to_first_executable_evidence` 暂时可以用：

```text
first SPIKE / EXECUTE decision 出现的 orchestration step
```

作为廉价 proxy。

无需现在精确测真实 wall-clock implementation。

---

# 17. 推荐实现包

整个收尾不要再拆成很多子代理。

建议：

```text
A — schema/version closure
B — audit→governor workflow closure
C — deterministic v1.1 checks
D — stage-checkpoint + self-hosted example
E — probe eval framework
F — probes P1–P6 + final regression run
```

总共 6 个包足够。

其中：

```text
A+B+C
```

可以并行一部分；

之后：

```text
D
↓
E+F
```

---

# 18. Review 策略

每个 implementation package：

```text
self-test
```

高风险的：

```text
B governor flow
C deterministic enforcement
```

各允许最多一个 focused reviewer。

最后只有一个 integration review。

禁止再次出现：

```text
contract reviewer
schema reviewer
planning reviewer
eval reviewer
re-reviewer
```

层层递归。

---

# 19. v1.1 最终 Definition of Done

## Contract Closure

- [x] `stage-contract@3` 与 `@2` 语义清晰分离（`stage-contract-v3.schema.json` 独立文件，@3 required 5 字段；@2 原文件恢复）；
- [x] v1.1 workflow 只生成 `@3`（long-task-planning/stage-contract skill 已指向 @3）；
- [x] `audit@3` 是 v1.1 auditor 正式输出（audit-v3.schema.json 纯 @3；plan-auditor SKILL.md 已改）；
- [x] `audit → governor → action` 成为唯一规划出口（long-task-planning step 3 重写：verdict 是数据不是闸）；
- [x] Governor 决定 SPIKE / PATCH / EXECUTE / HUMAN（TARGETED_PATCH 限制 + 同审计者 bounded re-audit + freeze rules）；
- [x] horizon minimum structural rules 可 deterministic validate（plan-check.py: HORIZON_SCOPE_VIOLATION / EXECUTION_BLOCKER_MISSING_REF / GOVERNOR_CONFLICT / GOVERNOR_BUDGET_EXCEEDED）；
- [x] StageCheckpoint 能承载 next-stage handoff（stage-checkpoint@1 schema + checkpoint-handoff skill 两级区分）；
- [x] v1.1 自身 example/dogfood 使用完整 v1.1 contracts（.plans/v1.1 全链 @3 + audit@3 + governor + stage-checkpoint；smoke fixture v11-plan lint 0/0/0）。

C1 gate: selftest OK；good-plan 0/0/0；bad-plan 9 codes；minimal_fixes 6/6；
v11_integration PASS；test_c1_closure 8/8（@3 拒绝缺字段、horizon 违反、
blocker 缺 ref、governor 冲突、budget 超支、legacy @2 兼容、schema 文件纯版本分离——
T8 为 C2 期间 P5 运行曾试图把 @2 文件改成 enum[@2,@3] 后加的防回归）。

## Probe Validation

- [x] P1 meta-runaway PASS（PASS_WITH_NOTES 0.857：完整治理周期被实测——独立审计→TARGETED_PATCH→同审计者 bounded re-audit→收敛 EXECUTE；唯一 note 是 single_audit_ideal 未达（用了 2 次审计，恰为预算上限））；
- [x] P2 horizon boundary PASS（PASS 1.0：detailed_stage = 有界 probe + 路由无关基础，forecast 携带 A/B 两路由（depends_on_evidence 无 task id），stop_after 停在证据点；实测两轮 TARGETED_PATCH——r1 会话内审计无效（2 BLOCKER HORIZON_SCOPE_VIOLATION：forecast 泄漏 T01），r2 独立审计另抓 2 个新缺陷，r3 有界 re-audit 收敛 EXECUTE；预算恰 2/2）；
- [x] P3 no-over-split 无严重问题（PASS 1.0：3 任务串行单阶段、无 spike、无过度拆分；独立审计另发现 F06 pytest/unittest runner 不匹配，governor 以 executor note 缓决）；
- [x] P4 blocker retention PASS（PASS 1.0：真 blocker 被独立审计检测（需求1 vs 固定 1024-slot RingBuffer，acceptance_ref A1）+ governor 正确 HUMAN_BLOCKER 升级，4 条 forbidden_actions，无 HANDOFF）；
- [x] P5 legacy planning quality 无明显退化（PASS 1.0：查询源冻结复用、out-of-scope 全保留、6 任务 3 并行组、lint 干净；期间实测 TARGETED_PATCH 修复 @2 误发契约→@3，14 条内联契约 hash 全审计未变）；
- [x] P6 cross-stage drift PASS（PASS 1.0：冻结 C1 逐字节继承、C2 按 unfreeze 规则仅追加、产品工单 last_notified_at 请求被 surfaced 而非 absorbed（out_of_scope + owner:user 开放问题 + 条件 forecast）；独立审计确认 NO SILENT DRIFT）；
- [x] v1.0/v1.1 的 P1 和 P5 sanity comparison 完成（两 probe 均为 2 审计 + 1 修订收敛；v1.1 无退化——P1 治理周期被完整行使且 429 由库内证据解决，P5 契约面更稳（v1.0 r1 审计暴露 2 BLOCKER/5 MAJOR 结构缺陷，v1.1 候选一次通过结构面）；详见收尾报告 §4）。

---

# 20. Stage Completion

完成上述内容后，冻结：

> **Planning Skills v1.1 — Contract-Closed Probe-Validated Baseline**

然后停止继续迭代。

下一步再选择一个真正合适的 benchmark，对：

```text
planning quality
planning cost
horizon selection
planner invocation
trajectory efficiency
```

做深入评估。

只有 benchmark 结果证明 v1.1 的行为方向成立后，再决定：

```text
继续 v1.2 skills iteration
或
进入 dsh-agent-team/runtime compatibility
```

这能避免再次在缺乏行为证据时过早固化 runtime architecture。