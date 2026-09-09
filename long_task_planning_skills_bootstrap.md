# 启动提示词：构造 Long-Task Planning Skills

你现在的任务是：**为本地 Agent 构造一组用于“长任务实现计划制订”的 Skills**。

这不是普通的“写计划模板”任务。目标是建立一套可复用的 Planning Compiler：把一个**任务边界已经明确、但实现规模较大、需要多个 Agent/多轮执行**的软件工程任务，编译成一个：

- 契约清晰；
- 上下文局部；
- 依赖明确；
- 可并行；
- 可验收；
- 可局部失败恢复；
- 可控制 token/context 成本；
- 不容易发生 scope creep 和无限长 run

的**可执行任务 DAG**。

请直接在当前仓库中完成 Skills 的设计、实现、文档与必要测试。不要只输出建议；要落盘形成可实际使用的 Skills。

---

# 1. 总体目标

这套 Skills 主要解决以下失败模式：

1. 一个本应有限的工程 Stage 在执行中不断吸收新问题，最终失控；
2. 计划按“功能/模块”机械拆分，导致每个执行 Agent 都必须重新读取大量仓库上下文；
3. Agent 在执行期间重新打开已经冻结的架构决策；
4. 任务之间依赖关系不清，导致不必要的串行，或错误并行造成文件/接口冲突；
5. 各个 leaf task 单独“完成”，但最终 integration 无法闭合；
6. leaf task 本身过大，单个 Agent run 跨越过多责任层、反复 compaction；
7. 出现 blocker 后不断 append 新任务，而不是 split / defer / replan；
8. 任务失败时无法局部恢复，只能让后续 Agent 重新考古整个 Stage。

最终目标不是“让计划更详细”，而是：

> 在保持实现质量的前提下，把长任务编译为上下文局部、契约稳定、可并行、可验收、可局部恢复的 execution DAG，并降低 context amplification、token 消耗、集成返工和极端长 run。

---

# 2. 核心方法论：必须落实到 Skills 中

以下原则不是背景说明，而是必须被 Skills 的 procedure、schema、checks 或 lint rules 实际执行。

## 2.1 Contract-first

先由专门的规划步骤定义并落盘**最小必要共享契约**，再解锁执行任务。

契约至少考虑：

- objective；
- in-scope；
- out-of-scope / non-goals；
- frozen assumptions；
- frozen architecture decisions；
- schema / API / service signatures；
- state transitions；
- ownership boundaries；
- error semantics；
- integration seams；
- deterministic acceptance criteria；
- resource constraints；
- allowed replan actions。

不要等待“完整总体设计”全部完成才允许下游实现。优先冻结那些能解锁并行工作的 shared seams。

---

## 2.2 Context-bounded decomposition

执行子任务的边界必须优先按：

> **完成该任务所需的最小上下文闭包**

而不是传统软件工程中的“功能”“模块”“目录”“页面”等边界来切分。

每个 leaf task 必须明确：

- Required Context；
- 必须读取的文件/目录；
- 必须理解的 contract；
- 必须掌握的概念；
- Owned Paths；
- Forbidden / unnecessary scope；
- Inputs；
- Outputs；
- Downstream consumers。

目标是最小化：

- 重复仓库读取；
- context switching；
- unrelated context loading；
- agent 再发现成本。

但也不能无限合并。若一个任务同时跨越过多责任层，例如：

UI → store → API → runtime → persistence → lifecycle → E2E

则必须检查能否在稳定 seam 处分割。

---

## 2.3 Executable DAG

必须根据真实 semantic dependency 构造 DAG，而不是把 Markdown 章节顺序当作执行顺序。

至少区分：

- contract dependency；
- data dependency；
- code ownership dependency；
- verification dependency。

必须显式识别：

- critical path；
- 可并行任务；
- 假串行；
- shared-file / shared-seam 冲突；
- 必须先冻结的 contract；
- integration gates。

优化目标是：

> **最小化 critical-path completion time 与 integration conflict，而不是最大化并发数。**

---

## 2.4 Freeze architecture during execution

执行 Agent 不得自行重开已经冻结的架构。

执行期间发现问题时，按以下三类处理：

### A. 当前任务必须修，否则无法完成
允许在当前任务内修复。

### B. 值得改善，但不影响当前 Stage 闭合
进入 follow-up / backlog，不进入当前任务。

### C. 原 contract / architecture 本身错误，导致任务无法正确实施
停止越界实现，产出：

- `CONTRACT_CHANGE_REQUEST`
或
- `CORE_SEAM_BLOCKER`

交还规划/集成层处理。

不能让执行 Agent 一边实现一边自行扩大 contract。

---

## 2.5 Every leaf is a bounded Task Package

每个 leaf task 至少应包含：

- ID；
- Objective；
- Required Context；
- Inputs；
- Frozen Contracts；
- Owned Paths；
- Allowed Dependencies；
- Explicit Non-goals；
- Implementation Constraints；
- Expected Outputs / Deliverables；
- Acceptance Criteria；
- Required Tests；
- Failure Cases；
- Integration Dependency；
- Handoff / Checkpoint requirements。

禁止出现只有：

> “实现 XX 功能”

这种不可直接执行的任务描述。

---

## 2.6 Deterministic closure

所有关键任务必须有可判真的 PASS / FAIL gate。

禁止只写：

- 完成；
- 完善；
- 优化；
- 确保正常；
- 充分测试。

验收应描述 observable behavior，并尽可能包含：

- positive case；
- negative case；
- failure behavior；
- required evidence。

---

## 2.7 Integration is explicit work

不得假设多个 leaf task 完成后会自然集成。

必须显式规划：

- contract consistency check；
- shared seam integration；
- integration-only fixes；
- E2E closure；
- migration / fixture / mock compatibility；
- final acceptance evidence。

Integration Agent 应优先依赖：

- frozen contracts；
- upstream outputs；
- changed paths；
- test evidence；
- checkpoints；

而不是重新读取整个项目。

---

## 2.8 Checkpoint and handoff

每完成稳定子目标，应能够生成机器可读或结构稳定的 checkpoint。

至少包含：

- current SHA / revision；
- completed task；
- contracts satisfied；
- changed paths；
- tests passed / failed；
- verified facts；
- deviations from plan；
- newly discovered issues；
- blockers；
- remaining DAG；
- downstream notes。

Checkpoint 的目标是成为：

> **context handoff artifact**

而不只是 Git commit。

---

## 2.9 Bound unhealthy runs

为 leaf task 设计“失控终止条件”。

至少考虑：

- 明显超过 P80 仍未接近 closure；
- context churn 持续扩大；
- 不断发现新的跨层依赖；
- 预计或实际发生多次 compaction；
- 连续 3 次 implementation attempt 仍无法通过同一个 gate；
- 同一任务被迫读取远超 Required Context 的范围。

此时默认行为不应是继续堆实现，而应产出：

- minimal reproducer；
- current diagnosis；
- failed attempts；
- blocker；
- relevant evidence；
- recommended split / escalation。

---

## 2.10 Context/token are planning resources

不要只估“代码量”。

至少考虑：

- context footprint；
- touched layers；
- cross-contract count；
- statefulness；
- integration distance；
- uncertainty；
- likely compaction risk；
- expected run length。

可采用以下经验性警戒线作为 heuristic，而非绝对 SLA：

- leaf P50：约 30–60 min；
- leaf P80：尽量 ≤ 90 min；
- 预计 4+ 次 compaction：强制检查是否应继续拆分；
- 10+ 次 compaction：默认视为 planning failure。

不要伪造过度精确的时间预测。必要时使用 S/M/L/XL 或 low/medium/high。

---

## 2.11 Replanning may shrink work

合法的 replan 动作至少包括：

- split；
- merge；
- reorder；
- change dependency；
- defer；
- reduce scope；
- replace implementation route；
- checkpoint-and-split；
- request contract revision。

禁止把 replan 简化为：

> 发现问题 → append 更多任务。

---

## 2.12 Local recoverability

计划应该具有：

> **局部失败、局部恢复**

的性质。

如果任意一个 leaf task 失败，会迫使整个 Stage 从头重启，则 DAG/contract/task package 设计通常仍不合格。

---

# 3. 建议的 Skill 组成

请优先实现以下核心 Skills。允许根据当前 Agent 框架的 skill 机制合并或调整文件结构，但职责必须保持清晰。

## 3.1 `stage-contract`

职责：

- 把用户任务编译成 Stage Contract；
- 明确 scope / non-goals；
- 冻结共享 seam；
- 定义 deterministic acceptance；
- 标记未解决 contract uncertainty。

建议输出结构：

```yaml
stage:
  objective:
  in_scope:
  out_of_scope:
  frozen_assumptions:
  frozen_architecture:
  shared_contracts:
  integration_seams:
  acceptance:
  constraints:
  resource_budget:
  allowed_replan:
```

---

## 3.2 `context-decomposer`

职责：

- 根据执行所需上下文构造候选 leaf tasks；
- 估计 context footprint；
- 识别 shared context 与 cross-layer coupling；
- 避免按功能/模块机械切分。

建议输出：

```yaml
task:
  id:
  objective:
  required_context:
    files:
    contracts:
    concepts:
  owned_paths:
  forbidden_scope:
  touched_layers:
  inputs:
  outputs:
```

关键 heuristic：

> 两项工作只有在“共享上下文带来的收益”大于“跨责任层耦合代价”时才合并。

---

## 3.3 `dependency-dag`

职责：

- 将任务编译成 DAG；
- 标记 dependency 类型；
- 找出 fake serialization；
- 检查 ownership collision；
- 提取 critical path；
- 给出合理 parallel groups。

建议输出：

```yaml
dependencies:
  T04:
    requires: [T01]
    reason:
    type:

parallel_groups:
  - [T04, T05]

critical_path:
  - T01
  - T04
  - T08
```

---

## 3.4 `task-packager`

职责：

把每个 leaf 编译成可直接交给 execution agent 的 Task Package。

固定 schema 至少包含：

```yaml
task_id:
objective:

required_context:
inputs:
frozen_contracts:

owned_paths:
allowed_dependencies:
non_goals:

implementation_constraints:

deliverables:

acceptance_tests:
failure_cases:

integration_dependency:

handoff:
  checkpoint:
  downstream_consumers:
```

执行 Agent 启动时应默认只读取 task package 指定上下文。只有出现证据证明上下文不足时才扩大读取范围，并记录理由。

---

## 3.5 `integration-planner`

职责：

- 显式识别 integration seams；
- 创建 integration tasks；
- 创建 E2E closure gates；
- 定义 integration-only fix ownership；
- 避免 leaf 完成但整体未闭合。

---

## 3.6 `plan-risk-estimator`

职责：

对每个 task 提供结构化风险估计，而非伪精确预测。

建议字段：

```yaml
context_footprint: S|M|L|XL
touched_layers:
cross_contracts:
statefulness: low|medium|high
integration_distance: low|medium|high
uncertainty: low|medium|high
p50:
p80:
compaction_risk:
warnings:
```

若 leaf 明显过大，应要求 planner 解释为何仍保持为单 leaf。

---

## 3.7 `plan-auditor`

必须由与原 planner 相对独立的审查路径使用。

审查至少包括：

- scope creep；
- insufficient non-goals；
- late contract freeze；
- hidden dependencies；
- fake serialization；
- ownership collision；
- oversized leaf；
- broad context loading；
- hidden integration work；
- nondeterministic acceptance；
- lack of local recoverability；
- replan-only-by-append；
- unnecessary reviewer/agent communication overhead。

问题等级建议：

- BLOCKER；
- MAJOR；
- MINOR。

BLOCKER 必须在执行前解决。

---

# 4. 可选运行时 Skills

如果当前框架适合，可以进一步实现：

## 4.1 `checkpoint-handoff`

生成稳定的任务交接记录。

## 4.2 `replan-controller`

仅在预定义 trigger 出现时调用，并限制 replan 的合法操作集合。

这两个 Skill 可以在 V1 后实现，但请预留接口。

---

# 5. Skills 的统一文件规范

每个 Skill 不得只是方法论文章。至少应包含以下内容：

## Trigger
何时调用；何时不调用。

## Inputs
调用前必须已有的输入。

## Procedure
清晰、顺序化、可执行的步骤。

## Heuristics
难以完全规则化时使用的判断原则。

## Output Schema
固定或半固定的机器可读结构。

## Failure / Escalation Criteria
什么时候停止正常流程并上报。

## Examples
至少一个 good case；如有必要加入 anti-pattern。

---

# 6. 总控 Workflow

请构造一个总控 planning workflow，大致遵循：

```text
User task
   │
   ▼
stage-contract
   │
   ▼
context-decomposer
   │
   ▼
dependency-dag
   │
   ├──► integration-planner
   │
   ▼
task-packager
   │
   ▼
plan-risk-estimator
   │
   ▼
plan-auditor
   │
   ├─ FAIL → targeted revision
   │
   └─ PASS
        │
        ▼
      execution
```

不要让 planner 完全自由地随意选择调用顺序。规划过程本身应尽可能 workflow 化。

---

# 7. V1 实现优先级

如果需要控制初版范围，优先保证以下六项可用：

1. `stage-contract`
2. `context-decomposer`
3. `dependency-dag`
4. `task-packager`
5. `plan-auditor`
6. `checkpoint-handoff`

`integration-planner` 的最小能力可先并入 DAG / auditor，但应保留独立升级空间。

`plan-risk-estimator` 第一版允许 heuristic 化，不需要伪精确耗时预测。

---

# 8. 计划产物目录建议

请结合当前仓库规范决定实际路径。若没有既有规范，可考虑：

```text
skills/
  long-task-planning/
    stage-contract/
    context-decomposer/
    dependency-dag/
    task-packager/
    integration-planner/
    plan-risk-estimator/
    plan-auditor/
    checkpoint-handoff/
    replan-controller/

schemas/
  planning/

docs/
  long-task-planning/

tests/
  planning-skills/
```

不要机械采用这个结构；优先遵循当前 Agent 框架已有 skill convention。

---

# 9. 实施要求

在开始写文件前：

1. 检查当前仓库已有 Skills 机制、格式和命名规范；
2. 找到已有高质量 Skill 示例；
3. 确认 Skill 如何被触发、加载、传参和测试；
4. 避免自行发明与宿主不兼容的格式；
5. 如果仓库已有 lint/schema/test infrastructure，复用它。

实施时：

- 尽量保持 Skills 短小、职责单一；
- 不要复制大量重复方法论文本；
- 共享 schema/术语应集中定义；
- 优先让 outputs 稳定、结构化、可被后续 Agent 消费；
- 任何自动化 heuristic 必须能够解释其判断依据；
- 不要把所有工作重新塞回一个“万能 planner skill”。

---

# 10. 完成条件

只有满足以下条件，才可以宣布本轮完成：

1. 核心 Skills 已实际落盘；
2. 存在一个可调用的总控 planning workflow 或清晰组合方式；
3. 每个核心 Skill 都有 Trigger / Inputs / Procedure / Output / Failure handling；
4. 存在统一的 Stage Contract 和 Task Package schema；
5. 存在至少一个完整示例，从长任务输入生成：
   - Stage Contract；
   - context-bounded tasks；
   - DAG；
   - Task Packages；
   - audit result；
6. 至少有基础测试或验证脚本证明 Skills 格式可被宿主正确加载；
7. 文档明确说明：
   - 如何调用；
   - 产物在哪里；
   - execution agent 应如何消费；
   - blocker / contract change 如何上报；
8. 不应把 Evals 的完整实现混入本任务；Evals 使用另一份启动提示词单独构造。

---

# 11. 最终输出要求

完成后请给出：

1. 实际新增/修改文件列表；
2. Skills 架构图或调用顺序；
3. 每个 Skill 的职责摘要；
4. 关键 schema；
5. 一个端到端示例；
6. 已执行的验证/测试及结果；
7. 尚未实现但建议进入 V2 的事项；
8. 任何可能影响后续 Evals 设计的接口约束。

请不要只给计划。**直接完成 Skills 的构造。**
