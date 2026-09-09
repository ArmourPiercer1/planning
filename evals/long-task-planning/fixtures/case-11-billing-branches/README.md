# case-11 — trap documentation (NEVER shown to planning subagents)

**Type K — local failure isolation.** The task literally says "two
independent branches". The trap is plans that couple them anyway:

- One "billing improvements" mega-task owning invoice.py + reports.py
  (cap is 1 anchor/task → flagged; cluster separate → violated).
- A cross-branch edge A1→A2 or A2→A1 (must_not_have — "failure in one must
  not re-plan the other" is the acceptance semantics).
- One branch restructuring the shared record format (freeze on A3).

Ground truth:
- Edges: A3→A1 (fee branch extends format additively), A3→A2 (report reads
  records). No A1↔A2 edge.
- `parallelizable_groups: [A1, A2]`.
- `recoverable_tasks: [A1, A2]` — BOTH branch tasks must carry
  checkpoint handoff requirements (the scorer checks the package's
  `handoff.checkpoint_required` for tasks covering these anchors). This is
  the local-recoverability dimension: if branch 1 dies mid-execution,
  branch 2 must be runnable from a clean checkpoint without branch 1.
- Range [3, 6], cap 1.
- The e2e gate must include the branch-isolation failure path (keywords:
  independent/isolated/does not affect/one branch) AND the late-fee path
  (5%/fee/overdue).

Scope bait: pdf/email/batch modules (must_not_expand).
