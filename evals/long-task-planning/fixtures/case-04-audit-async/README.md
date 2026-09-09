# case-04 — trap documentation (NEVER shown to planning subagents)

**Type D — fake serialization (doc order).** The narrative ("the API stops
writing, then the worker starts persisting") invites a serial
`API task → worker task` edge. In the code, the two sides only meet through
the event contract: topic `audit` + field set `{ts, actor, action, entity,
amount}` (constants live in `ledger/api.py`, bus in `ledger/events.py`).

Ground truth:
- Real edges: A2→A1 and A2→A2→A3 (contract-first). `must_have_edges`
  requires both.
- `must_not_have_edges: A1 ↔ A3` — a direct producer→consumer edge is the
  trap. Note the scorer treats a single task covering both anchors as
  internalized (not a violation) — the blob plan is punished elsewhere
  (max_anchors_per_task = 1, cluster separate).
- `parallelizable_groups: [A1, A3]`.
- Range [3, 6], cap 1: expected shape = contract task + producer task +
  consumer task (+ e2e gate task), or contract folded into one of the two
  sides with the other side still separate.
- The worker already dedupes (`make_audit_consumer`) — a good plan treats
  idempotency as part of the frozen contract and the e2e gate includes the
  duplicate-delivery failure path (marker keywords: duplicat /
  at-least-once / idempot).

Traps:
- Serial API→worker chain (flagship).
- One blob "async audit" task owning api.py + worker.py (cap violation).
- Invented scope: audit reports, web UI, archival policy
  (must_not_expand).
- Changing the field set or topic name "to clean up" (contract break).
