# case-02 — trap documentation (NEVER shown to planning subagents)

**Type B — same module, different contexts.** All three files live in one
tiny package, which tempts a plan to treat "durable SMS" as one task. The
contexts are genuinely different:

- `sender.py` — carrier runtime (deterministic reject rules; frozen by the
  task itself).
- `store.py` — persistence format (the on-disk queue + record shape).
- `cli.py` — command wiring (the only place both are joined).

Key facts:
- `sender` and `store` are mutually independent (no imports either way).
  `must_not_have_edges: A1 ↔ A2` encodes that ordering them is invented.
- `max_anchors_per_task: 1` — a task that owns both `sender.py` and
  `store.py` is a context merge the case wants flagged.
- The message record shape is given in the task prompt; a good plan still
  freezes it as a shared contract (must_freeze A2+A3, kind contract) and an
  e2e gate covers crash recovery + duplicate dispatch.

Traps:
- One blob task touching all three files (leaf_boundedness + cluster
  violation).
- Invented scope: web UI, message templates, a retry-policy module —
  listed in must_not_expand_scope.
- Forgetting that `dispatch_command` must return attempted ids in queue
  order (acceptance detail; scored via acceptance determinism, not a hard
  constraint).
