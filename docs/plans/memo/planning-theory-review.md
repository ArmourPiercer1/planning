# 长任务 Agent 规划的相关理论综述
## 从一次性大计划到受约束的滚动时域控制

**用途**：为 Long-Task Planning Skills 的下一阶段设计提供理论基线。  
**核心问题**：在目标与硬约束已经定义良好的前提下，怎样让 Agent 只对必要的近端工作做详细规划，在执行产生新证据后再规划下一阶段，同时避免 scope、架构、质量标准与预算发生长期漂移。

---

## 1. 结论摘要

对长时间 Agent 软件工程任务而言，最值得吸收的不是单一的“项目管理方法”，而是以下研究路线的组合：

1. **Model Predictive Control / Receding-Horizon Control**  
   只对有限未来做优化，只执行近端决策，观测真实状态后重新求解。
2. **Rolling-Horizon / Rolling-Wave Planning**  
   区分近期承诺区、当前详细规划区、远期粗略预测区，避免过早详细展开。
3. **Event-Triggered / Self-Triggered Control**  
   不在每个时刻都重新规划；只有状态偏差、风险、预算或阶段完成等事件满足触发条件时才调用昂贵 planner。
4. **Dual Control / Information-Gathering Control**  
   行动不仅追求任务进展，也可以主动获取能改变后续决策的信息；implementation spike 是合法的一类控制动作。
5. **Rational Metareasoning / Value of Computation**  
   “继续思考一次”本身有成本。Planner 必须判断额外规划是否值得延迟和 token/模型成本。
6. **Spiral Model / Risk-Driven Development**  
   下一阶段优先处理最可能改变路线、造成返工或阻塞交付的风险，而不是机械按模块推进。
7. **Stage-Gate 及其后续修正**  
   阶段结束时做 Go/Continue/Redirect 决策是有价值的，但 Gate 过多会官僚化；一个真正阶段对应一个真正 Gate 更合理。
8. **Contract-Based / Assume-Guarantee Design**  
   长期稳定的 Project Contract、短期 Stage Contract 和 Worker Guarantee 可以形成可组合的长期连续性。
9. **Robust MPC / Tube 思想**  
   “实际执行偏离具体计划”不应自动视为漂移；真正要限制的是状态是否离开允许的 contract corridor。
10. **Recursive Feasibility**  
    每个阶段不仅要完成自己的目标，还要保证结束状态仍然“可继续规划”，即 recursive plannability。
11. **Set-Based Design / Real Options**  
    在证据不足时保留多个未来路线，推迟不可逆决策；不应把远期 forecast 误冻结为具体实施承诺。
12. **Simplex / Runtime Assurance**  
    强 planner 可以提出复杂方案，但应由一个更确定性的 governor 检查其是否违反硬约束，再交给便宜 Executive 执行。
13. **Continual Planning / HTN / MAPE-K**  
    规划与执行应交错；层次化 roadmap 应 lazy decomposition；监控、分析、规划、执行和知识状态最好分离。
14. **现代 Multi-Agent Agent 架构**  
    Magentic-One 的 Task Ledger / Progress Ledger、outer planning loop / inner progress loop 和 stall-triggered replanning 是值得参考的工程实例。

这些理论共同指向一个统一范式：

> **Contract-constrained, event-triggered, receding-horizon planning with executable evidence.**

---

# 2. 为什么一次性全任务规划容易失败

一次性大计划隐含三个过强假设：

1. 当前已经知道足够多的未来 repo/runtime 状态；
2. 现在做出的远期任务划分和依赖关系在十几个小时后仍然有效；
3. 为消除未来不确定性投入更多规划计算，总体上总是有益。

在真实软件工程 Agent 工作流中，这三个假设通常都不成立。

执行会持续产生高价值新信息：

- public seam 的真实行为；
- 现有 abstraction 是否足够；
- integration 是否成立；
- 测试与真实 host 的差异；
- 原本“必须”的 feature 是否可以降级；
- 原本以为简单的 seam 是否是 blocker。

因此，越远期的详细计划越容易成为 **planning waste**。

更合理的控制问题不是：

> “怎样一次把 30 小时任务规划正确？”

而是：

> “怎样只规划到当前信息仍足以支持可靠承诺的位置，并保证之后还能继续规划而不漂移？”

---

# 3. Model Predictive Control：最核心的结构类比

Mayne、Rawlings、Rao 与 Scokaert 对 constrained MPC 的经典综述把 MPC 描述为：

- 以当前状态作为初始状态；
- 在线求解有限时域优化问题；
- 得到一段未来控制序列；
- 只执行其中最前端的控制；
- 下一采样时刻根据新状态重新求解。

对 Agent 长任务：

| MPC | Agent Planning |
|---|---|
| plant state \(x_k\) | Project / repo checkpoint |
| system model | 当前对代码、工具、运行时的认知 |
| constraints | Project Contract / hard invariants |
| prediction horizon | 当前 Stage + 粗 roadmap |
| optimized controls | Stage Plan |
| first applied control | 当前 commitment window |
| measurement | tests / diff / runtime evidence |
| re-optimization | 下一次高智力 planner 调用 |

关键启示不是“每一步都重规划”，而是：

> **远期可以预测，但只有近端进入 commitment。**

这应成为下一代 Planning Skills 的最高层原则。

---

# 4. 三个 Horizon：Commitment / Detailed / Forecast

滚动时域调度和 rolling-wave planning 的重要经验是：不要把所有未来内容视为同一种“计划”。

建议显式维护三个 horizon。

## 4.1 Commitment Horizon

已经 dispatch、正在执行、或已经对外形成强承诺的内容。

特征：

- 不因普通新发现而改写；
- 只有真正 blocker / human override 才允许取消；
- Executive 对这一层负责。

## 4.2 Detailed Planning Horizon

当前 Stage。

需要：

- leaf tasks；
- dependency；
- ownership；
- acceptance；
- retry/fallback；
- 当前必要 contract；
- 资源与时间盒。

High-IQ planner 主要在这一层工作。

## 4.3 Forecast Horizon

未来阶段只保存：

- stage objective；
- 粗依赖；
- 主要风险；
- 可选路线；
- 预计信息前提。

禁止提前生成大量 leaf task 和精细 DAG。

### 设计结果

未来计划应允许写成：

```yaml
roadmap:
  - stage: capability-core
    status: current
  - stage: live-wiring
    status: forecast
    depends_on_evidence:
      - filesystem-spike
      - ask-bridge-spike
  - stage: alpha-candidate
    status: forecast
```

而不是在当前时刻就把第三阶段展开成 T17/T18/T19。

---

# 5. Event-Triggered Control：什么时候重新规划

Event-triggered / self-triggered control 的动机之一就是：控制或优化计算本身昂贵，没有必要以固定高频率重新求解。

对应 Agent 系统，高智力 planner 应成为 **episodic resource**。

建议 planner trigger 至少包括：

```text
1. 当前 Stage acceptance 已满足；
2. frozen assumption 被证伪；
3. public seam / external dependency 结果改变下游路线；
4. 实际执行状态显著偏离 Stage 的 forecast；
5. critical path / budget envelope 显著变化；
6. progress stall 超过阈值；
7. 出现真正需要修改 Project Contract 的 blocker；
8. 当前 Stage 已到预先定义的 planning horizon。
```

以下默认不触发强 planner：

```text
- worker 第一次失败；
- 局部 fixture 问题；
- 普通机械 merge conflict；
- 非阻塞 bug；
- SHOULD feature 延期；
- 局部测试修复。
```

这将“什么时候调用更强模型”从习惯问题变成控制策略。

---

# 6. Dual Control：执行与信息获取可以是同一个动作

Dual control 研究未知系统中的 exploration/exploitation：动作既改变系统，又产生对系统参数的新信息。

Agent 软件工程中的 implementation spike 就是典型 dual-purpose action。

例如：

```text
问题：public filesystem seam 是否安全支持 subtree？

路线 A：
继续读源码、写 contract、拉 reviewer。

路线 B：
做一个 45 分钟最小 spike/test，验证 exact/subtree 行为。
```

路线 B 同时产生：

- implementation progress；
- executable evidence；
- 对未来路线的高信息增益。

因此 Stage planner 应显式允许：

```yaml
task_type: implementation_spike
objective:
  progress: optional
  information_gain: primary
timebox: 60m
decision_after:
  pass: ship subtree
  fail: exact-only and defer subtree
```

Spike 不应被视为“规划失败后的补救”，而应是正常控制动作。

---

# 7. Metareasoning：Planning 本身也必须受成本约束

Russell 与 Wefald 的 rational metareasoning 把“计算动作”本身视为有成本的决策。

可以把是否继续规划近似写为：

\[
VOC(P)
=
E[\Delta C_{\text{downstream}}]
-
C_{\text{planner}}
-
C_{\text{delay}}
\]

其中：

- \(E[\Delta C_{\text{downstream}}]\)：额外规划预计减少多少返工/风险；
- \(C_{\text{planner}}\)：强模型、token、上下文重建成本；
- \(C_{\text{delay}}\)：等待规划导致的 wall-clock 延迟。

2024 年 AAAI 的 *Stop! Planner Time* 进一步直接研究“继续规划还是开始执行当前方案”的 metareasoning policy。

对 Planning Skills 的直接结论：

> **Schedule estimator 应是 forecast，不应变成要求反复 replan 直到 P80 形式上满足预算的 certification loop。**

必须有 planning budget、audit budget 和 stopping rule。

---

# 8. Spiral Model：下一 Stage 应由风险而不是模块名决定

Boehm 的 Spiral Model 是 risk-driven 软件过程模型。

对 Agent 工作流，Stage selection 应优先问：

> “当前哪个未知最可能改变路线、造成大量返工、破坏 hard invariant 或阻塞交付？”

而不是：

> “接下来应该开发 backend 还是 frontend？”

例如某个 alpha 的 Stage 1 可能只有两个 spike，因为它们决定后面所有 wiring 的可行性。

这意味着 Planning Skills 需要一个 `stage-boundary / stage-selector` heuristic：

```text
优先把“高路线影响 + 可快速获得证据”的 uncertainty 放进当前 Stage。
```

---

# 9. Stage-Gate：有 Gate，但不要 Gate 化一切

Stage-Gate 的价值：

- 阶段收集信息；
- Gate 做质量检查与继续投入决策；
- 下一阶段资源在 Gate 处重新承诺。

但 Cooper 后续也明确指出传统 Stage-Gate 可能过慢、浪费时间、官僚化，因此第三代过程强调 fluid、flexible、situational/fuzzy gates；后续 Agile–Stage-Gate hybrid 更进一步强调适应性。

对 Planning Skills：

> **一个真正 Stage ≈ 一个真正 Gate。**

不要：

```text
一个 contract → 一个 Gate
一个 adapter → 一个 Gate
一个 DTO → 一个 Gate
```

Leaf 默认 self-test；高风险 leaf 最多一个 focused reviewer；完整 independent gate 留给阶段/candidate。

---

# 10. Contract-Based Design：滚动计划如何不漂移

滚动规划最大风险是长期目标漂移。

Assume–Guarantee / Contract-Based Design 给出非常自然的组织方式：

\[
A \Rightarrow G
\]

建议三层 contract：

## Project Contract

长期稳定：

```yaml
objective:
acceptance:
hard_invariants:
non_goals:
delivery_profile:
budget_envelope:
frozen_decisions:
```

## Stage Contract

只承诺当前 horizon：

```yaml
assumes:
guarantees:
objective:
acceptance:
budget:
uncertainty_to_resolve:
commitment_boundary:
next_planning_trigger:
```

## Worker Contract

局部 Task Package：

```yaml
assumes:
guarantees:
owned_paths:
tests:
fallback:
```

Worker guarantee 形成 Stage guarantee；Stage guarantee 成为下一 Stage 的 verified assumption。

关键是显式维护：

```text
verified assumptions
falsified assumptions
still-unverified assumptions
```

这比保存完整对话历史更能防 drift。

---

# 11. Robust MPC：Drift 不是“计划改变”，而是越出允许走廊

Tube MPC 的思想是：面对模型误差，不要求实际轨迹严格贴合 nominal trajectory，只要求其保持在允许的 tube 中。

映射到 Agent planning：

错误的 drift 定义：

```text
actual execution != detailed plan
```

更好的定义：

```text
actual state violates Project Contract corridor
```

Contract corridor 可以包括：

```text
必须完成核心 acceptance
不得突破安全/权限 hard invariant
不得 core patch
不得偷偷扩大 scope
delivery profile 不得从 alpha 漂成 RC
预算不得无限膨胀
```

Stage 中发生：

```text
T3 → spike → T5
```

即使与最初详细顺序不同，也未必是 drift。

因此 Drift Detector 应检测：

- requirement removal；
- unauthorized scope addition；
- frozen decision change；
- assurance level change；
- budget-envelope violation；
- hard invariant violation。

而不是检测每一次 plan deviation。

---

# 12. Recursive Feasibility → Recursive Plannability

MPC 关心 recursive feasibility：

> 当前动作执行后，下一时刻仍然存在满足约束的可行控制。

对应长任务，建议定义：

## Recursive Plannability

每个 Stage 结束时必须保证：

```text
1. repo / artifact 处于稳定 checkpoint；
2. 当前 Stage guarantee 已可验证；
3. 没有未记录的架构漂移；
4. 没有 half-applied shared state；
5. 下一阶段关键输入清楚；
6. remaining project acceptance 仍然可达；
7. 失败/延期项均有显式 disposition。
```

这是比“把整个未来 DAG 规划完”更强的长期性质。

只要每个 Stage 都保持 recursive plannability，就不需要在 Stage 1 预测 Stage 7 的 leaf task。

---

# 13. Set-Based Design / Real Options：远期路线不要过早冻结

Set-Based Design 反对在高不确定性早期过早收敛到单一 point design，因为后续新信息会造成高返工。

未来 roadmap 可以保存 option set：

```yaml
future_route_options:
  filesystem_policy:
    - subtree_via_public_seam
    - exact_only_alpha
decision_trigger:
  - fs_spike_result
```

原则：

> **冻结 invariant；不要冻结尚无证据支持的实施选择。**

这也修正了简单的“contract-first = 越早冻结越好”误读。

Contract-first 应意味着：

> 越早冻结真正共享且成熟的 seam；  
> 未成熟的选择保持显式 uncertainty / option。

---

# 14. Simplex：强 Planner 提案，确定性 Governor 放行

Simplex runtime assurance 的核心结构是：

```text
Advanced Controller
+
Baseline/Safe Controller
+
Decision Module
```

对 Agent 系统，可以映射为：

```text
High-IQ Strategic Planner
        ↓ proposes
Planning Governor
        ↓ admits / rejects / cuts
Cheap Executive
        ↓ dispatches
Workers
```

High-IQ Planner 可以有创造性，但不直接拥有无限执行 authority。

Governor 检查：

- Project Contract；
- delivery profile；
- scope；
- planning budget；
- Stage size；
- forbidden modifications；
- reviewer/replan budget；
- public-seam rule。

这非常适合未来与 dsh-agent-team 的权限/状态机结合。

---

# 15. MAPE-K 与 Continual Planning：职责分离

Autonomic computing 中常见的 MAPE-K 思路：

```text
Monitor
Analyze
Plan
Execute
Knowledge
```

对未来系统：

```text
Monitor:
  收集 TaskResult / tests / budgets / runtime state

Analyze:
  drift/stall/assumption invalidation

Plan:
  episodic High-IQ Planner

Execute:
  cheap Executive + workers

Knowledge:
  ProjectContract
  StagePlan
  Checkpoint
  Evidence ledger
```

Distributed Continual Planning 也早已指出，动态环境中 planning 与 execution 需要 interleave，而不是一次 plan 后长期执行。

---

# 16. HTN：保留层次，但 lazy decomposition

HTN 很适合表达：

```text
Deliver alpha
├ capability core
├ live wiring
└ validation
```

但不意味着一开始就把所有 compound task 展开到 primitive task。

建议：

> **hierarchical roadmap + lazy decomposition + receding horizon**

只有进入 current detailed horizon 的 Stage 才展开 leaf tasks。

---

# 17. Magentic-One：一个值得参考的现代 Agent 工程实例

Magentic-One 的 Orchestrator 维护：

- Task Ledger；
- Progress Ledger；
- outer loop；
- inner loop；
- progress stall 后更新 Task Ledger / replan。

值得吸收的不是具体 prompt，而是结构：

```text
长期任务状态
≠
每一步执行进度
```

你的设计可以进一步拆成：

```text
Project Contract / Roadmap
Stage Plan
Progress / Checkpoint
```

并把 outer planner 从持续运行的 Orchestrator 中抽出来，改成 episodic high-IQ service。

---

# 18. 统一形式化

可以把系统状态写为：

\[
x_k = \mathrm{Checkpoint}_k
\]

Project Contract 定义允许状态集合：

\[
x_k \in \mathcal C
\]

高智力 planner 在事件触发时求一个有限 Stage plan：

\[
\pi_k = P(x_k,\mathcal C,H_k)
\]

只 commit 当前近端 Stage：

\[
S_k
\]

Executive 执行：

\[
x_k \xrightarrow{S_k} x_{k+1}
\]

阶段结束检查：

### Constraint preservation

\[
x_{k+1}\in \mathcal C
\]

### Stage acceptance

当前 guarantee 成立。

### Recursive plannability

存在下一阶段：

\[
\exists S_{k+1}
\]

### Planner trigger

当：

\[
g(\text{drift},\text{uncertainty},\text{risk},\text{budget},\text{stall})>\tau
\]

时重新调用 High-IQ planner。

---

# 19. 对 Planning Skills 的直接设计原则

建议冻结以下原则：

1. **近端详细、远端粗略。**
2. **只 commit 当前 Stage。**
3. **Planner 是事件触发的稀缺资源。**
4. **Planning 本身有预算。**
5. **可执行 spike 优先于重复推测可观测事实。**
6. **Stage 按风险和信息增益划分，不按模块机械划分。**
7. **未来 implementation option 在证据不足时保持开放。**
8. **Project Contract 定义 corridor；plan deviation 不等于 drift。**
9. **Stage 必须保证 recursive plannability。**
10. **一个 Stage 一个真正 Gate；避免 contract/gate proliferation。**
11. **强 planner 只提案；Governor 决定是否允许进入执行。**
12. **Executive 负责状态机，不负责重新解释目标。**
13. **Checkpoint 传递证据和状态，不传递完整历史。**
14. **Eval 必须测 planning cost、time-to-first-evidence 和 plan churn。**

---

# 20. 推荐阅读与来源

## Model Predictive Control
- Mayne, D. Q., Rawlings, J. B., Rao, C. V., & Scokaert, P. O. M. (2000). *Constrained model predictive control: Stability and optimality*. Automatica 36(6), 789–814. DOI: https://doi.org/10.1016/S0005-1098(99)00214-9

## Robust / Tube MPC
- Langson, W., Chryssochoos, I., Raković, S. V., & Mayne, D. Q. (2004). *Robust model predictive control using tubes*. Automatica 40(1), 125–133. https://doi.org/10.1016/j.automatica.2003.08.009

## Event-Triggered MPC
- 相关综述入口：ScienceDirect Topics, *Event-Triggered Control*: https://www.sciencedirect.com/topics/engineering/event-triggered-control

## Dual Control
- Chen, W.-H. et al. (2022). *Perspective view of autonomous control in unknown environment: Dual control for exploitation and exploration vs reinforcement learning*. Neurocomputing 497, 50–63. https://doi.org/10.1016/j.neucom.2022.04.131
- Meijer, T. J., & Rantzer, A. (2026). *Dual Control: On Exploration-Exploitation in Linear Systems*. arXiv:2608.20073.

## Rational Metareasoning
- Russell, S., & Wefald, E. (1991). *Principles of metareasoning*. Artificial Intelligence 49, 361–395. https://doi.org/10.1016/0004-3702(91)90015-C
- Budd, M., Lacerda, B., & Hawes, N. (2024). *Stop! Planner Time: Metareasoning for Probabilistic Planning Using Learned Performance Profiles*. AAAI 38(18), 20053–20060. https://doi.org/10.1609/aaai.v38i18.29983

## Spiral / Risk-Driven Development
- Boehm, B. W. (1988). *A Spiral Model of Software Development and Enhancement*. Computer 21(5), 61–72. https://doi.org/10.1109/2.59

## Stage-Gate
- Cooper, R. G. (1994). *Third-Generation New Product Processes*. Journal of Product Innovation Management 11(1), 3–14. https://doi.org/10.1111/1540-5885.1110003
- Cooper, R. G., & Sommer, A. F. (2016). *The Agile–Stage-Gate Hybrid Model*. Journal of Product Innovation Management 33(5), 513–526. https://doi.org/10.1111/jpim.12314

## Contract-Based Design
- Benveniste et al. / assume-guarantee contract literature；一个公开入口：*A Boolean Algebra of Contracts for Assume-guarantee Reasoning*, 2010. https://doi.org/10.1016/j.entcs.2010.05.007

## Set-Based Design
- Shallcross, N., & Parnell, G. (2020). *Set-based design: The state-of-practice and research opportunities*. Systems Engineering. https://doi.org/10.1002/sys.21549
- Dullen, S. (2021). *Survey on set-based design quantitative methods*. Systems Engineering. https://doi.org/10.1002/sys.21580

## Continual Planning
- desJardins, M., Durfee, E., Ortiz, C., & Wolverton, M. (1999). *A Survey of Research in Distributed, Continual Planning*. AI Magazine. https://www.sri.com/publication/artificial-intelligence-pubs/a-survey-of-research-in-distributed-continual-planning/

## HTN
- Georgievski, I., & Aiello, M. (2015). *HTN planning: Overview, comparison, and beyond*. Artificial Intelligence 222, 124–156. https://doi.org/10.1016/j.artint.2015.02.002

## Runtime Assurance / Simplex
- Mehmood, U. et al. (2021). *The Black-Box Simplex Architecture for Runtime Assurance of Autonomous CPS*. arXiv:2102.12981.

## Autonomic Computing
- White, S. R. et al. (2006). *Autonomic computing: Architectural approach and prototype*. Integrated Computer-Aided Engineering 13(2). https://doi.org/10.3233/ICA-2006-13206

## Modern Multi-Agent Reference
- Microsoft AutoGen, *Magentic-One Architecture*: https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/magentic-one.html

---

# 21. 对本项目的理论定位

这套 Planning Skills 的远期理论定位可以表述为：

> **面向软件工程 Agent 的、受 Project Contract 约束的、事件触发的、滚动时域层次化规划与执行控制系统。**

它不是为了生成“完美的全局 DAG”，而是为了：

> **在有限推理与执行资源下，使长期目标持续可达，同时让每一阶段都尽早产生可执行证据，并在必要时使用更高智力重新优化下一阶段。**
