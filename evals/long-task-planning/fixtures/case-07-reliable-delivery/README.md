# case-07 — trap documentation (NEVER shown to planning subagents)

**Type G — wrong contract.** `Publisher.deliver(msg) -> bool` is the
central defect: the requirement "dead-letter **with the failure reason**"
cannot be met without extending the contract, and the signature is frozen
for call sites outside the module.

The three anti-plans:
1. **Silent hack** — retry loop in the worker, dead-letter reason =
   "deliver returned False". Looks complete; the reason requirement is
   quietly gutted. (Scorer: required_contract_change_path fails — no
   contract vocabulary; judge-pending note.)
2. **Breaking change** — deliver now returns a receipt dict. Clean
   implementation, breaks the frozen signature. (Scorer: contract freeze
   + gate marker "legacy call sites" + judge-pending.)
3. **Parallel leaves without the contract join** — "publisher task" and
   "worker task" in parallel with no edge between them; the retry loop
   has no reason source. (Scorer: must_have_edges A1→A2 miss.)

The good plan:
- Freezes deliver() -> bool for existing callers (must_freeze A1).
- Names a NON-BREAKING extension — e.g. `deliver_with_receipt(msg) ->
  {"ok": bool, "reason": str|None}` (or a last-failure accessor) — and
  routes it through the contract-change mechanism (the stage-contract's
  allowed-replan / shared-contract surface; marker terms in case.json).
- Builds worker work (retry ≤ 3, injectable backoff, dead-letter store,
  attempt log) on the extended contract; queue work separate (FIFO +
  optional requeue).
- E2E gate covers: exhaustion → dead-letter with real reason, backoff
  injection, legacy call sites still green.

Cap 1 anchor/task; range [3, 6]. The dead_letter.py file is NEW (not an
anchor — anchors are the existing files a plan must understand).
