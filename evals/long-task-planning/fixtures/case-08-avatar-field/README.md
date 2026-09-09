# case-08 — trap documentation (NEVER shown to planning subagents)

**Type H — oversized leaf.** Five files, five layers, ~40 lines of actual
change. The volume whispers "one task", and the naive plan does exactly
that: `T01 implement avatar_url` owning models+validators+service+handlers+
serializers. A fresh executor for that task must load all five closures at
once — the textbook oversized leaf.

Scoring levers:
- `max_anchors_per_task: 2` — the mega task (4-5 anchors) is over cap.
- `acceptable_task_count_range: [3, 6]` — mega task = 1-2 tasks, under
  range.
- `phase_shaped_leaves` (scorer) — tasks with >12 context files or >=4
  anchors are named in the report.
- `must_have_edges` (A1→A3, A2→A3, A3→A4, A1→A5) — a plan that collapses
  everything into one task internalizes the edges (allowed — internalized
  edges count as hit), so edges alone can't catch the mega task; the cap +
  range + boundedness do.
- `parallelizable_groups: [A1, A2]` — model and validator work are
  disjoint; a decent plan parallelizes them.

Freezes that separate good from bad:
- owner-only contract (ride the existing PermissionError path — don't build
  a second ownership check in the handler).
- omission rule in the public shape (key absent, not null) — an explicit
  consumer contract; the e2e gate must cover both the rejection and the
  omission.

Scope bait: avatars_store / upload endpoint / migrations (URL-only feature).
