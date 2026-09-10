# Planning Skills v1.1 收尾报告：Contract Closure + Probe Validation

> 状态：**CLOSED — 基线已冻结**（见 §7）
> 范围文档：`docs/plans/active/Planning Skills v1.1 收尾计划：Contract Closure + Probe Validation.md`
> 审查约束（全部遵守）：无大 benchmark、无统计显著性、无重复采样、无 LLM judge、无 runtime/plugin 状态机、无 dsh-agent-team 集成；每个 probe 仅 1 个候选运行；C2 只用 C1 候选；probe 失败 → 定点补丁 + 重跑该 probe + 核心 smoke。

---

## 1. 结论

- **C1 Contract Closure：完成。** v1.1 契约面（stage-contract@3 / audit@3 / governor-decision@1 / stage-checkpoint@1 / probe-run-result@1）与 v1.0 面（@2/@1 纯版本文件）分离完毕；`audit → governor → action` 成为唯一规划出口；4 条 deterministic 检查（HORIZON_SCOPE_VIOLATION / EXECUTION_BLOCKER_MISSING_REF / GOVERNOR_CONFLICT / GOVERNOR_BUDGET_EXCEEDED）上线；回归锚全部绿（§5）。
- **C2 Probe Validation：6/6 探针全部 PASS 级**（P1 PASS_WITH_NOTES 0.857，P2–P6 PASS 1.0）。P4 按设计停在 HUMAN_BLOCKER（真 blocker 保留）。v1.0/v1.1 的 P1、P5 sanity comparison 完成（§4）：**v1.1 无质量退化，治理机制被真实行使，代价是审计轮数增加（P1/P2/P5 均用满或接近 2 次审计预算）**。
- 冻结：**Planning Skills v1.1 — Contract-Closed Probe-Validated Baseline**。按 §20 停止迭代。

---

## 2. C1 Contract Closure 结果

| 项 | 结果 |
|---|---|
| stage-contract@3 / @2 语义分离 | ✅ `stage-contract-v3.schema.json` 独立纯 @3（5 个新 required 字段）；`stage-contract.schema.json` 从 `59b78e3` 恢复纯 @2 |
| v1.1 workflow 只生成 @3 | ✅ long-task-planning step 3 + stage-contract skill 输出节指向 @3 |
| audit@3 正式化 | ✅ `audit-v3.schema.json` 纯 @3（enum→const）；plan-auditor SKILL.md 改；finding 携带 routing + acceptance_ref |
| audit → governor → action 唯一出口 | ✅ step 3 重写；verdict 是数据不是闸；governor 4 动作表 + TARGETED_PATCH 规则 + freeze rules |
| StageCheckpoint 承载 handoff | ✅ `stage-checkpoint.schema.json` @1 新建；checkpoint-handoff skill 两级区分（checkpoint@2 任务级 vs stage-checkpoint@1 阶段级） |
| deterministic 检查 | ✅ plan-check.py 4 条新检查，只在 @3 工件/governor 存在时触发 |
| dogfood | ✅ `.plans/v1.1/` 全链 @3 + audit@3 + governor EXECUTE + stage-checkpoint，lint 0/0/0；fixture `v11-plan` 升级同规格 |

**C1 gate（全绿）**：selftest OK；good-plan 0/0/0；bad-plan 9 tracked codes；minimal_fixes 6/6；v11_integration PASS；`test_c1_closure` 8/8。

**C2 期间追加（由 probe 暴露）**：
1. **P5 运行曾试图把 `stage-contract.schema.json` 的 schema 字段改成 `enum [@2, @3]`**（编排器自称"harness-level fix"）。已回滚，并加 T8 防回归（@3 声明工件必须不能通过 @2 文件直接验证，反之亦然）。教训：probe 运行期间禁止修改候选物本身，补丁只允许落在工件。
2. **plan-auditor SKILL.md 隔离条款自相矛盾**（"orchestrator 可显式降级隔离" vs AUDIT_NOT_ISOLATED 硬闸）。已在探针前定点修正：隔离不可降级；会话内审计必须如实记 `planner_conversation_isolated: false` 并被硬闸拒绝，唯一正路是换独立审计路径。修正后 P3/P5/P6 的会话内审计均按此替换为独立审计。

---

## 3. C2 Probe Validation 结果（v1.1 候选）

| 探针 | 问题 | 判定 | 分数 | 关键观察 |
|---|---|---|---|---|
| P1 meta-runaway | 未知 429 语义会不会诱发 runaway 规划？ | **PASS_WITH_NOTES** | 0.857 | 完整治理周期实测：独立审计（PASS+1 MAJOR）→ governor TARGETED_PATCH（stop_after 漏 T02）→ 同审计者 bounded re-audit（F01 解决）→ 收敛 EXECUTE。429 由库内 staging 证据解决为冻结假设（A-429-TRANSIENT），无 spike、无阻塞开放问题。唯一 note：用了 2 次审计（恰为预算上限），single_audit_ideal 未达 |
| P2 horizon boundary | 路由未知时会不会 over-plan？ | **PASS** | 1.0 | detailed_stage = 有界 reader-inventory probe + 路由无关 YAML store；forecast 携带 A/B 两路由（仅 objective + depends_on_evidence，无 task id）；stop_after 停在证据点。实测**两轮** TARGETED_PATCH：r1 会话内审计（无效隔离）抓出 2 BLOCKER HORIZON_SCOPE_VIOLATION（forecast 泄漏 T01）→ 补丁 → r2 独立审计另抓 2 个 r1 漏掉的缺陷（A1 矩阵 2 项无 owning test、AT-T01-2 正则假阴）→ 补丁 → r3 bounded re-audit PASS → EXECUTE。预算恰 2/2 |
| P3 no-over-split | 已知路线会不会被过度拆分/虚假 spike？ | **PASS** | 1.0 | 3 任务串行单阶段（T01 模块 → T02 接线 → T03 e2e+seam 合并），无 spike，horizon 全 detailed 无 forecast。独立审计补抓 F06（证据命令用 pytest 但 repo 是 stdlib unittest）→ governor 以 executor note 缓决（多工件 MINOR，按 P1/P5 先例不触发补丁） |
| P4 true-blocker retention | 真 blocker 会不会被"解决"掉？ | **PASS** | 1.0 | **按设计停在 HUMAN_BLOCKER。** 独立审计判定需求 1（全历史链、随时可验、任何截断/改写破坏）在固定单 1024-slot 覆盖写 RingBuffer 约束下**结构不可满足**（grounding：storage.py + test_ring_overwrites_oldest + README），且计划擅自把用户未决策的产品语义冻结为假设（A-CHAIN-WINDOW）→ F01 BLOCKER/EXECUTION_BLOCKER（acceptance_ref A1）+ F02 MAJOR/EXECUTION_BLOCKER（C1 哈希输入不含 payload，验收却要求检测 payload 改写 → 按冻结规范执行者必红）。governor 正确升级：4 条 forbidden_actions（禁执行、禁决策前修订、禁 3 次审计、禁换审计者）、预算预留、无 HANDOFF（blocked run hands off nothing） |
| P5 legacy planning quality | 真实业务任务规划质量有无退化？ | **PASS** | 1.0 | 查询单源冻结复用（C2 引 `app/queries.report_with_rows`）、out-of-scope 全保留（email/edit/archive + 2 项 grounded 补充）、6 任务 3 并行组、lint 0 BLOCKER。期间编排器误发 @2 契约（horizons 空）被独立审计抓出（F01 MAJOR）→ TARGETED_PATCH 重发 @3 → bounded re-audit 全 14 条内联契约 hash 复验未变 → EXECUTE |
| P6 cross-stage drift | 跨 stage 会不会静默改冻结契约？ | **PASS** | 1.0 | **漂移陷阱未被采纳**：产品工单要求把 `last_notified_at` 嵌入 GET /todos（破坏冻结 C1）→ 未被吸收，out_of_scope + 非阻塞开放问题（owner: user，产品签核）+ 条件 forecast 预声明；C1 逐字节继承（含 em-dash），C2 按 unfreeze 规则仅追加 `webhook_url?`。独立审计**程序化**确认 NO SILENT DRIFT（raw byte 比对 + sha256） |

**审计隔离纪律**：P1/P4/P5/P2(从 r2 起) 使用 fresh isolated auditor 子代理；P3/P6 原会话内审计按硬闸规则替换为独立审计（无效隔离记录不计入已接受审计预算——此记账裁定统一适用于 P2/P3/P5/P6）。独立审计的边际价值被两次实证：P2 r2 抓到 r1 漏的 2 个缺陷；P5/P6 各抓到会话内审计漏掉的 MAJOR/manifest 无效。

---

## 4. v1.0 vs v1.1 sanity comparison（P1、P5）

### P1（429 未知 + 优化诱导）

| 维度 | v1.0 基线 | v1.1 候选 |
|---|---|---|
| 判定 | PASS_WITH_NOTES（记录性，7/7 检查） | PASS_WITH_NOTES（0.857，6/7） |
| 审计轮数 | 2（r1 FAIL：1 BLOCKER 隐藏依赖 + 1 MAJOR 幻影输入；r2 PASS） | 2（r1 PASS+1 MAJOR；r2 bounded re-audit F01 解决） |
| 修订轮数 | 1（v1.0 定向修订环） | 1（TARGETED_PATCH） |
| 任务数 | 3（稳定） | 2 |
| 未知处理 | 冻结假设 A-429-RETRYABLE + 验证叶 T01（与 T02 并行，T03 门控 verdict） | 冻结假设 A-429-TRANSIENT（库内 staging 证据，冻结前查证） |
| 优化/健壮性诱导 | bulk 入 out_of_scope；无 storm 叶 | bulk 入 out_of_scope + governor 缓决；无 storm 叶 |

**读法**：两者都 2 审计 + 1 修订收敛，成本相当。v1.0 的 r1 审计更"硬"（BLOCKER 级结构缺陷），v1.1 的 MAJOR 在 horizon 面（stop_after 覆盖）。v1.1 的增量：路由/缓决显式化、horizon 治理被验证有效（P2 才见全貌）。**无 runaway、无假 blocker、无诱导采纳——v1.0 在此探针上也不差，v1.1 未退化。**

### P5（真实业务任务：报告导出）

| 维度 | v1.0 基线 | v1.1 候选 |
|---|---|---|
| 判定 | PASS_WITH_NOTES（记录性，7/7 检查） | PASS（1.0，5/5） |
| 任务数/结构 | 7（4 全并行叶 + 3 集成：consistency / seam / e2e 分立） | 6（3 叶 + 3 集成，seam 并入 e2e_closure） |
| 并行度 | 4 叶完全并行（零叶间边，3 条 fake-serialization 移除记录） | 3 并行组 |
| 审计轮数 | 2（r1 FAIL：2 BLOCKER + 5 MAJOR + 60 MINOR 共 67 项；r2 PASS：1 MINOR 表面级） | 2 次已接受（r2 独立 PASS+1 MAJOR；r3 bounded re-audit F01 解决）+ 1 次无效会话内 r1 |
| 修订轮数 | 1（定向修订：C1 body 矛盾、C2 缺 customer_id、allowed_replan 补齐、58 处措辞重写） | 1（TARGETED_PATCH：@2 误发契约重发 @3 + 3 项 MINOR） |
| 查询单源复用 | ✓（C3 冻结 app/queries.py） | ✓（C2 引 `report_with_rows`） |
| 范围保持 | ✓（4 项 out-of-scope，email/edit/archive 全列） | ✓（email/edit/archive + 2 项 grounded 补充） |
| 最终 lint | 0 findings（r1 后 62 → 修订后 0） | 0 BLOCKER / 17 MINOR（风格类，缓决） |

**读法**：两者都是 2 审计 + 1 修订收敛，成本相同。v1.0 的 r1 审计暴露了更重的结构缺陷（C1 下载体 "base64-or-bytes-ref" 与全部验收矛盾、C2 job record 缺 customer_id 的隐藏依赖），说明 v1.1 候选的契约起草质量更高（一次通过结构面，MAJOR 只在 horizon 声明面）；v1.0 为此多改了 58 处措辞文本。v1.1 的 17 条 MINOR 是 EVIDENCE_MARKERS 启发式假阴（§6.1），非实质缺陷。**v1.1 无质量退化，契约面反而更稳。**

**保真度备注**：P5 基线编排器在"会话内审计（按派发说明）"与"v1.0 skill 自身硬规则（stage 7 永远 fresh subagent）"之间选择了后者，两轮审计均为 fresh isolated 子代理——这是对基线保真度的正确选择（基线要忠实复现 v1.0 行为，v1.0 skill 本就要求独立审计），已在运行记录中如实披露。

---

## 5. 回归锚（commit 前终检，全绿）

- `plan-check.py selftest` → OK
- `fixtures/good-plan` lint → 0/0/0
- `fixtures/bad-plan` lint → 9 tracked codes（8B/2M/3m，含 2 条既有）
- `fixtures/minimal_fixes` → 6/6 修复后通过
- `tests/planning-skills/v11_integration` → PASS
- `tests/planning-skills/test_c1_closure` → 8/8
- `fixtures/v11-plan`（dogfood 同规格）lint → 0/0/0
- `.plans/v1.1/`（契约级 dogfood：contract→audit→governor→stage-checkpoint 链，非 8 阶段完整目录——目录级 lint 的 MISSING_ARTIFACT 对部分目录属预期，非回归；4 个工件逐文件 validate 全 ok）

---

## 6. 遗留观察（不构成 v1.2 工作，记录在案）

1. **EVIDENCE_MARKERS 正则假阴**：`\btest\b` 不匹配 `tests.` / `test_x`，多个运行出现 VAGUE_ACCEPTANCE 假报（P1 4 条、P3 10 条、P4 21 条→已措辞规避、P5 17 条）。属 MINOR 级风格启发式，各独立审计均逐条复核确认为确定性表述。候选改进：marker 正则支持 `tests\.` 前缀。
2. **run-manifest.json 不在 lint 覆盖内**：P5/P6 两次出现 manifest 自身 schema 无效而 lint 绿灯（独立审计才发现）。候选改进：lint 增加 manifest 自检。
3. **审计预算记账**：无效隔离审计不计入已接受审计——目前由父编排器逐运行裁定（P2/P3/P5/P6 同规则）。候选改进：把该规则写进 planning-governor skill 的 budget 小节，免去逐运行裁定。
4. **P2 编排器曾试图把预算记账改成 full_audits=2（含无效 r1）并预写 forbidden_actions**，与自身决策文本冲突，由父裁定纠正。属执行偏差，机制本身（governor 记录 + 硬闸）未失守。

---

## 7. 冻结

按范围文档 §20，自本报告提交起冻结：

> **Planning Skills v1.1 — Contract-Closed Probe-Validated Baseline**

此后不启动 v1.2 设计、不做 runtime 工作、不加 benchmark。遗留观察（§6）留待未来版本另行立项。

---

## 附录：产物清单

- 候选物（C1）：`.agents/schemas/planning/{stage-contract-v3,checkpoint-v2,stage-checkpoint,probe-run-result}.schema.json`（新）+ `stage-contract.schema.json`/`checkpoint.schema.json`（恢复纯版本）+ `audit-v3.schema.json`（const）；`.agents/scripts/plan-check.py`（registry + 4 检查）；4 个 skill 修订（long-task-planning / plan-auditor / planning-governor / checkpoint-handoff）
- 测试与 dogfood：`tests/planning-skills/test_c1_closure.py`（8 测试）；`tests/planning-skills/fixtures/v11-plan/`；`.plans/v1.1/`
- 探针基础设施：`evals/probes/{README.md,run_probe.py,merge_baseline.py}`；`evals/probes/repos/p1…p6`（6 个任务 repo）；`evals/probes/baseline-v1.0/{skills,scripts,schemas,references}`（从 `59b78e3` 二进制安全提取）
- 运行记录：`evals/probes/runs/{p1,p2,p3,p4,p5,p6}-v1.1-r1/`（各含 plan/ 全链工件 + run-manifest + HANDOFF）；`evals/probes/runs/{p1,p5}-v1.0-r1/`（baseline）；`evals/probes/results/`（7 份 probe-run-result@1，P1/P5 含 baseline 嵌入字段）
