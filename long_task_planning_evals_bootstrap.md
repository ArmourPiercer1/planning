# 启动提示词：构造 Long-Task Planning Skills 的 Evals

你现在的任务是：**为“长任务实现计划制订 Skills”构造一套可重复运行、尽可能自动化、能够比较不同版本效果的 Evals。**

这不是让另一个 LLM 对计划“打 8.7/10 分”。目标是建立一套能真正判断 Planning Skills 是否降低长任务执行成本和失控概率的评估体系。

请直接在当前仓库中实现 eval fixtures、runner、scoring、reporting 和必要文档。不要只输出建议。

---

# 1. 被评估系统的目标

Planning Skills 的目标是：

> 把一个边界已经明确的长软件工程任务编译成上下文局部、契约稳定、依赖明确、可并行、可验收、可局部失败恢复的 execution DAG，并降低执行过程中的 context amplification、token 消耗、集成返工、scope creep 和极端长 Agent run。

因此 Evals 不应只检查：

- 计划是否详细；
- Markdown 是否漂亮；
- 是否列了很多步骤；
- LLM judge 是否“觉得不错”。

必须尽可能测量：

- Stage completion；
- critical-path wall time；
- token / context cost；
- task boundedness；
- context locality；
- dependency correctness；
- integration rework；
- scope creep；
- replan quality；
- local recoverability；
- compaction / extremely long run tail risk。

---

# 2. 评估原则

## 2.1 不要求唯一正确 DAG

长任务计划通常不存在唯一 ground truth。

因此 benchmark 应为每个 case 定义：

- 必须发现的依赖；
- 禁止出现的依赖；
- 必须冻结的 seam；
- 必须存在的 acceptance gate；
- 不应进入当前 scope 的问题；
- 不能并行修改的 ownership；
- 可接受的任务粒度范围；
- 必须显式存在的 integration behavior；
- 必须允许的 failure/replan path。

即评估**约束满足程度**，而不是要求生成完全相同的计划文本。

---

## 2.2 优先使用程序化评分

能用静态规则、repo diff、runtime telemetry 或 test result 判定的内容，不要交给 LLM judge。

LLM judge 只用于：

- 难以形式化的 context grouping 合理性；
- contract 清晰度；
- non-goal 是否真正消除了歧义；
- 计划解释是否自洽。

即使使用 LLM judge，也必须：

- 固定 rubric；
- 给出证据；
- 尽量 pairwise 比较；
- 避免只给单一主观分数。

---

## 2.3 评估不仅看平均值，还要看 tail

Planning Skills 的价值之一是防止极端失控。

因此必须关注：

- P90 / P95 task duration；
- max task duration；
- max context read；
- max compactions；
- catastrophic replan；
- stage restart frequency。

不能只看平均 token 或平均完成时间。

---

## 2.4 计划效果应记录为向量，而不是单一总分

建议主要结果表示为：

```text
E = (
  success,
  wall_time,
  tokens,
  context_read,
  rework,
  integration_defects,
  scope_creep,
  replans,
  compactions,
  local_recoverability
)
```

可以额外生成 composite score 方便排序，但不能丢弃原始维度。

---

# 3. Evals 应包含四层

请构造以下四层评估。若执行成本受限，优先完整实现 Layer 1 + Layer 2，并为 Layer 3 + Layer 4 提供可运行骨架。

---

# Layer 1：Static Plan Quality

输入：

- 用户任务；
- 仓库/fixture；
- Planning Skills 生成的 Stage Contract、DAG、Task Packages 等。

不执行真正实现，只分析计划结构。

至少评估以下指标。

---

## 3.1 Contract Completeness

检查 Stage Contract 是否定义：

- objective；
- in-scope；
- out-of-scope；
- frozen assumptions；
- frozen architecture / contracts；
- acceptance；
- integration seams；
- constraints；
- allowed replan。

可计算：

```text
contract_completeness =
defined_required_fields / total_required_fields
```

注意：字段存在但为空泛时不应算完整。

---

## 3.2 Acceptance Determinism

检查第三方是否能够仅根据 acceptance 判断 PASS / FAIL。

自动检查 anti-pattern：

- “完成”
- “完善”
- “优化”
- “确保正常”
- “充分测试”
- “合理”
- “尽可能”

但不要只靠关键词。必要时加入 rubric judge。

---

## 3.3 Context Locality / Context Amplification Risk

检查每个 leaf：

- requested files 数量；
- requested directories 范围；
- 是否要求阅读整个 repo；
- 是否读取大量不相关模块；
- required context 是否与 owned paths / contracts 相匹配。

可记录：

```text
context_amplification_proxy =
unique_context_files_requested / max(1, files_expected_to_change)
```

如果真实执行可获取 telemetry，再使用真实值替代 proxy。

---

## 3.4 Ownership Collision

对被计划为并行的任务检查：

- owned paths overlap；
- shared core file overlap；
- shared contract write conflict。

至少输出：

```text
parallel_ownership_collisions
```

并区分：

- benign overlap；
- serialized seam；
- hazardous collision。

---

## 3.5 Dependency Precision

检查：

- missing dependency；
- redundant dependency；
- cycle；
- fake serialization；
- dependency without reason/type；
- integration dependency 缺失。

对于 benchmark fixture，使用 case 定义的 must-have / must-not-have edges 自动判分。

---

## 3.6 Leaf Boundedness

对每个 leaf 记录：

- touched layers；
- cross-contract count；
- context footprint；
- statefulness；
- integration distance；
- predicted P50/P80（如有）；
- compaction risk。

重点查找明显仍然是 Phase 的“leaf”。

---

## 3.7 Integration Explicitness

检查：

- 是否存在 integration task / gate；
- 是否定义 contract consistency check；
- 是否定义 E2E closure；
- 是否明确 integration-only fixes 的 ownership。

---

## 3.8 Recoverability

评估：

> 删除任意一个 leaf 的执行结果，是否只需要重做局部 DAG？

可设计近似指标：

```text
local_recoverability =
locally_recoverable_tasks / all_tasks
```

Benchmark case 应能标记哪些任务必须具有局部恢复路径。

---

## 3.9 Scope Discipline

检查计划是否吸收 fixture 中明确标记为：

- non-blocking tech debt；
- unrelated refactor；
- future optimization；
- optional cleanup

的问题。

记录：

```text
scope_creep_items_planned
```

---

# Layer 2：Planning Challenge Benchmark

请构造一组**小型、可控、故意包含规划陷阱的 repo/task fixtures**。

目标不是模拟完整大型项目，而是让每个 case 精确测试一个或两个 planning failure mode。

建议初版 12–20 个 case，后续扩展到 30–50 个。

每个 case 应包含：

```yaml
id:
description:
repo_fixture:
task_prompt:

expected:
  must_freeze:
  must_not_expand_scope:
  must_have_dependencies:
  must_not_have_dependencies:
  parallelizable_groups:
  forbidden_parallel_pairs:
  required_integration_gates:
  acceptable_task_count_range:
  required_failure_paths:
  expected_context_clusters:
```

---

## 4.1 Case 类型

至少实现以下类型。

### Case A：假功能边界

一个“功能”实际跨多个目录，但实现上下文自然分成两个或三个 clusters。

目标：

检查 planner 是否按 context closure 拆分，而不是按 feature 名称做一个巨大 task。

---

### Case B：同模块但上下文不同

同一 feature 中：

- runtime semantics；
- UI wiring；
- persistence/reload；
- E2E

需要不同上下文。

目标：

检查 planner 是否能够拆开。

---

### Case C：假并行

两个看似独立任务最终都必须修改同一个 state machine / shared schema。

目标：

检查是否发现 ownership / contract conflict。

---

### Case D：假串行

两个任务在需求文档里前后出现，但不存在真实 dependency。

目标：

检查 planner 是否不必要地串行。

---

### Case E：隐藏 integration seam

backend 与 UI 均可独立完成，但 response schema 有轻微不一致。

目标：

检查是否显式规划 integration gate，而不是假设自然闭合。

---

### Case F：诱导 scope creep

repo 中存在明显技术债、TODO 或不优雅设计，但完全不阻塞本 Stage。

目标：

检查是否被错误纳入当前计划。

---

### Case G：错误 contract

给出一个表面完整、但不能支持目标行为的接口。

目标：

检查计划是否提供：

- `CONTRACT_CHANGE_REQUEST`
或
- `CORE_SEAM_BLOCKER`

路径，而不是鼓励 execution agent 偷偷修改架构。

---

### Case H：超大 leaf

一个表面单一的功能实际涉及：

UI + API + persistence + lifecycle + tests。

目标：

检查是否识别 oversized leaf。

---

### Case I：共享 context 适合合并

两个不同模块的修改都依赖同一个复杂状态模型，而且修改量都很小。

目标：

防止 planner 过度追求“每模块一个 task”，也防止过度细碎拆分。

---

### Case J：integration-only bug

所有 leaf unit tests 均可通过，但组合后失败。

目标：

检查 integration task / E2E gate。

---

### Case K：local failure

一个 branch 失败不应阻塞另一个无关 branch。

目标：

检查 DAG 是否支持局部继续执行与局部恢复。

---

### Case L：需要 replan 但不应扩 scope

一个实现路径失败，有另一条等价实现路线。

目标：

检查 replan 是否优先 replace route / split，而非不断 append unrelated tasks。

---

# 5. Layer 3：Execution-based Eval

在一批中小型、可重复的软件工程任务上实际执行计划。

建议任务规模覆盖：

- ~30 min；
- ~1 h；
- ~2 h；
- ~4 h；

不要一开始就用几十小时真实项目做 A/B。

至少比较：

## Baseline A
单 Agent 自己计划、自己执行。

## Baseline B
普通 todo/checklist planning。

## Candidate
Long-Task Planning Skills pipeline。

如资源允许，再加入：

- Candidate without auditor；
- Candidate without context-decomposer；
- Candidate without integration-planner。

---

## 5.1 执行指标

### Completion Rate

Stage 是否通过最终 acceptance。

---

### Wall-clock Critical Path

记录：

```text
stage_wall_time
critical_path_time
```

并区分 worker 并发造成的总计算时长与用户实际等待时间。

---

### Token Consumption

至少记录：

```text
total_input_tokens
total_output_tokens
per_task_tokens
```

如宿主提供 cached token，也单独记录。

---

### Context Read Volume

至少尝试记录：

```text
files_opened
unique_files_opened
lines_read
repo_fraction_read
```

若无法获得 lines，可先使用 file-level telemetry。

---

### Rework Ratio

建议近似：

```text
rework_ratio =
later_overwritten_or_reverted_lines /
total_implemented_lines
```

或根据 commits/diff overlap 构造可重复 proxy。

---

### Integration Defect Rate

在 leaf tasks 均声称完成后，integration 阶段发现的 defect 数量。

---

### Plan Deviation

记录：

- split；
- merge；
- cancel；
- reorder；
- contract revision；
- unplanned task count。

不要简单认为 deviation 越少越好；重点区分健康 replan 与 uncontrolled expansion。

---

### Run Length Distribution

记录：

- P50；
- P90；
- P95；
- max；
- compaction count；
- retries per task。

重点观察 tail。

---

# 6. Layer 4：Long-task Robustness / Fault Injection

在执行到某个固定阶段时注入扰动，测试 graceful degradation。

至少设计以下 fault injection。

---

## 6.1 Contract mismatch injection

执行中发现 frozen contract 与真实实现不兼容。

预期：

- 局部停止；
- 生成 contract-change / blocker；
- 不允许 worker 偷偷修改公共 seam；
- 不需要 Stage 全量重启。

---

## 6.2 Worker failure

一个并行 worker 中途失败。

预期：

- 无关 branches 继续；
- 可从 checkpoint 局部恢复；
- 不要求其他 agent 重新读取整个 Stage。

---

## 6.3 Runtime overrun

把某个 leaf 的真实耗时人为变成预计 P80 的约 3 倍。

预期：

- 触发 unhealthy-run / replan 机制；
- 不无限续跑。

---

## 6.4 Non-blocking bug discovery

执行时暴露一个真实但不阻塞当前 Stage 的 bug。

预期：

- 记录 follow-up；
- 不吸收进当前 scope。

---

## 6.5 Context expansion pressure

执行任务需要一个额外文件，但不需要整个目录。

预期：

- 允许受控扩大；
- 记录原因；
- 不演化成全仓扫描。

---

## 6.6 Integration failure

各 leaf 单测均通过，但 E2E integration 失败。

预期：

- 能定位到 seam；
- integration task 接管；
- 不导致所有 leaf 重新执行。

---

# 7. 核心结果指标

至少报告以下指标，不要只生成单一分数。

| 指标 | 目标 |
|---|---:|
| Stage completion rate | ↑ |
| Wall-clock critical path | ↓ |
| Total tokens | ↓ |
| Context read volume | ↓ |
| P95 single-agent run length | ↓ |
| Integration rework | ↓ |
| Scope-added-during-execution | ↓ |
| Compactions / completed task | ↓ |
| Local recoverability | ↑ |

两个特别重要的诊断指标：

```text
Context Amplification =
unique files read /
max(1, files actually required to change)
```

以及：

```text
Integration Rework =
integration-stage changed lines /
max(1, total changed lines)
```

如果更合理，可以采用更稳定的 proxy，但必须记录定义。

---

# 8. Ablation Eval

必须设计 ablation capability。

至少支持：

```text
Full
Full - context-decomposer
Full - plan-auditor
Full - integration-planner
Full - risk-estimator
```

重点观察：

## 去掉 context-decomposer

预期可能导致：

- token ↑；
- files read ↑；
- task duration tail ↑。

## 去掉 integration-planner

预期可能导致：

- 单 leaf 速度变化不大；
- integration defect / rework ↑。

## 去掉 plan-auditor

预期可能导致：

- 平均值变化不大；
- catastrophic planning failure ↑。

Evals 应能够验证这些假设是否真实成立，而不是预设结论。

---

# 9. Baseline 设计

至少保留两个稳定 baseline。

## Baseline A：Free-form Agent Planning

只给原始任务，让同一 Agent 自由规划与执行。

## Baseline B：Conventional Checklist Planning

要求生成传统：

- Phase；
- Todo；
- implementation checklist；

但不提供 context-bounded / contract-first / DAG 专门 Skills。

Candidate 与 baseline 应：

- 使用相同模型；
- 相同工具；
- 相同 repo 起点；
- 相同 task prompt；
- 尽量相同 token/runtime limits。

避免模型差异污染结果。

---

# 10. Benchmark 数据组织

若当前仓库无既有规范，可考虑：

```text
evals/
  long-task-planning/
    fixtures/
      case-a/
      case-b/
      ...
    expected/
    runners/
    scorers/
    reports/
    baselines/
    fault-injection/
    schemas/
```

但优先遵循现有 eval framework。

每个 fixture 必须：

- 足够小；
- 可快速 reset；
- 可重复执行；
- 包含明确 hidden trap；
- 有自动 test；
- 有机器可读 expected constraints。

---

# 11. Runner 要求

Eval runner 至少应支持：

- 指定 case；
- 批量运行；
- 指定 candidate/baseline；
- 重复 N 次；
- 固定或记录模型配置；
- 保存完整计划产物；
- 保存执行 trace；
- 保存 token/context telemetry；
- 保存 repo diff；
- 保存 tests；
- 保存 failure reason；
- 生成机器可读结果。

建议结果 schema 类似：

```yaml
run_id:
case_id:
planner_variant:
model:
seed_or_run_index:

planning:
  contract_score:
  dependency_score:
  context_locality:
  ownership_collisions:
  integration_explicitness:
  recoverability:

execution:
  success:
  wall_time:
  input_tokens:
  output_tokens:
  unique_files_read:
  files_changed:
  rework_ratio:
  integration_defects:
  scope_creep_items:
  replans:
  compactions:
  max_task_duration:

artifacts:
  plan:
  trace:
  diff:
  tests:
```

---

# 12. LLM Judge 的使用规范

如果需要 LLM judge，只允许用于难以静态判定的维度。

每个 rubric 必须：

- 有明确 0/1/2 或 1–5 定义；
- 要求引用计划中的具体证据；
- 禁止仅凭整体印象评分；
- 尽量采用 blind pairwise；
- 不向 judge 暴露哪个是 Candidate、哪个是 Baseline；
- 保存 judge reasoning summary 与证据位置；
- 对关键 benchmark 不应让 LLM judge 成为唯一裁判。

---

# 13. 防止 Eval 被“刷分”

请检查并防止以下 gaming：

1. planner 为降低 context 数量而遗漏必要上下文；
2. planner 为降低 task duration 而过度碎片化；
3. planner 为避免 ownership collision 而全部串行；
4. planner 为提高 recoverability 而制造大量无意义 checkpoints；
5. planner 为降低 integration defects 而把所有任务塞进一个巨型 integration task；
6. planner 把所有潜在问题都写成 blocker，逃避正常执行；
7. planner 用极宽泛 acceptance 伪造高 completion rate。

因此指标必须成组解释，而不是单指标优化。

---

# 14. V1 优先级

若需要控制初版工作量，优先实现：

## P0
1. Static Plan Quality scorer；
2. 12–20 个 Planning Challenge fixtures；
3. Baseline A / B；
4. Candidate runner；
5. 机器可读结果；
6. 一份汇总报告。

## P1
7. Execution-based eval；
8. context/token telemetry；
9. ablation。

## P2
10. Fault injection；
11. 长时间 robustness；
12. 多模型交叉验证。

不要为了追求一开始就“完整”而让 Eval 框架本身变成长任务失控案例。

---

# 15. 初版验收标准

本轮只有满足以下条件才算完成：

1. 存在可运行的 eval runner；
2. 至少 12 个独立 planning challenge cases；
3. 每个 case 有机器可读 expected constraints；
4. Static scorer 能输出结构化结果；
5. 至少支持：
   - Free-form baseline；
   - Checklist baseline；
   - Skills candidate；
6. 能生成 aggregate report；
7. 报告至少包含：
   - contract completeness；
   - dependency correctness；
   - ownership collision；
   - context locality proxy；
   - integration explicitness；
   - scope discipline；
   - recoverability；
8. 至少有一个 execution-based smoke eval；
9. 至少有一个 ablation 示例；
10. 文档说明：
   - 如何新增 case；
   - 如何运行；
   - 如何读取结果；
   - 哪些指标不能单独解释；
   - 如何防止 benchmark gaming。

---

# 16. 最终输出要求

完成实现后，请给出：

1. Eval 架构与目录；
2. 已实现 case 列表及其测试目标；
3. Baseline 与 Candidate 的调用方式；
4. Scoring 规则；
5. Runner 使用方法；
6. 一次实际 smoke run 的结果；
7. 生成的报告位置；
8. 当前无法自动化、仍依赖 judge 的指标；
9. 你认为最容易被 benchmark gaming 的地方；
10. 下一版最值得加入的 robustness / execution eval。

请不要只提供评估方案。**直接完成可运行的 Evals 基础设施。**
