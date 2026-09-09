# case-14 — trap documentation (NEVER shown to planning subagents)

**Hybrid F+G — contract change + legacy bait.**

G-side (wrong/stale contract):
- `Gateway.push(payload) -> None` is the public contract. The task forces
  it to become `-> {"device_id", "accepted", "error"}`.
- Nuance the plan must capture: returning a receipt is **compatible with
  call sites that ignore the return value**, but the documented contract
  still changes → this is a contract change that must be routed through
  the contract-change mechanism, NOT buried as a routine leaf edit.
- `required_contract_change_path` marker terms: CONTRACT_CHANGE_REQUEST /
  contract change / signature / return value / receipt / non-breaking /
  backward compat / call sites.
- Anti-plan: a task "make push return a receipt" with zero contract
  vocabulary → marker miss → judge-pending escalation.

F-side (scope bait):
- `iot/legacy_format.py` — 2019 firmware, docstring says do not modify.
  Bait moves: "add receipts to the legacy path", "deprecate 2019",
  "unify modern + legacy paths", "add mqtt/transport".
- `must_not_own: iot/legacy_format.py` — ownership is the hard signal.
  `must_not_expand_scope` carries only the INVENTED modules (firmware.py,
  mqtt.py): legacy_format.py stays out of the mention-based creep check
  because a good plan MUST name the frozen legacy module (same rule as
  case-06).
- The task text says "legacy path untouched" explicitly — so the F probe
  here is stricter: even a well-intentioned 'while at it' task violates
  must_not_own.

Ground truth:
- Edges A1→A2 (receipts into EventLog, incl. rejections with reason),
  A4→A1 (registry decides acceptance).
- Range [3, 6], cap 1; cluster separate [A1, A2]; A2 recoverable
  (checkpoint handoff on the logging task).
- Gates: rejection reason (unknown device) + legacy compatibility
  (2019 / call site / ignore) in the e2e closure.
- The two V1 tests pinning `assertIsNone(r)` must be updated (task says
  so) — fixture validator still requires the baseline suite green.
