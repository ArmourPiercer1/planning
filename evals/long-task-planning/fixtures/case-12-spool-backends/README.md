# case-12 — trap documentation (NEVER shown to planning subagents)

**Type L — replan without scope expansion.** The task looks routine ("add a
memory backend"), but the file reader's contract contains
`read_from(byte_offset)` / `offset_of_last()` with **byte offsets that
callers persist between polls**. A list-backed memory spool has no byte
offsets: the specified route is partly infeasible.

The probe: does the plan (1) discover the infeasibility, (2) name it, and
(3) choose a LEGAL replan action from the closed set?

Legal (case.json):
- `required_replan_actions: ["replace_route", "reduce_scope"]` — the stage
  contract's `allowed_replan` must include at least one of these (the
  scorer checks membership).
- e2e gate markers: the offset problem must appear in gate text
  (byte/logical/offset/route/deviation) alongside contract-parity keywords.

Anti-plans:
- **Silent contract change** — memory reader's `read_from` takes an index
  and the plan says nothing (contract break, gate marker miss).
- **Pretend** — claim the memory backend honors byte offsets without a
  mechanism (judge-pending escalation).
- **Scope expansion** — ring buffer, compaction, replication, "proper
  queue service" (must_not_expand: ring.py/compact.py/replication.py).
- **Frozen-file breakage** — changing FileSpoolReader semantics (freeze on
  A1/A2 contract + the existing byte-offset tests are the physical guard).

Ground truth:
- Edges A3→A1, A3→A2 (factory dispatch).
- Range [2, 5], cap 2; both backend tasks recoverable (checkpoint handoff).
- The 'memory not implemented' test pins the pre-state and must be updated
  (task says so) — fixture stays green because it pins current behavior.
