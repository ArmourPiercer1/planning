# case-09 — trap documentation (NEVER shown to planning subagents)

**Type I — merge shared context.** Two "domains" (sales, inventory) both
read the same tiny shared file (`rules.py`), and a third caller (`tax.py`)
is frozen. The total change surface is ~2 call sites + 1 test update. The
trap is the reverse of most cases: **over-fragmentation**. The two-domain
language invites "fix sales" / "fix inventory" / "guard tax" / "understand
rules" as separate tasks; the honest structure is 1-2 tasks over one merged
closure.

Scoring levers:
- `acceptable_task_count_range: [1, 2]` — 3+ tasks is out of range.
- `context_clusters: merge [A1..A4]` — a plan where no single task covers
  all four anchors fails the merge check.
- `max_anchors_per_task: 4` — deliberately permissive so the merged task
  is legal; the mega-task detector (>=4 anchors in leaf_boundedness) still
  flags a single task with a huge context list.
- `must_freeze` A1 behavior + A4 behavior: rules default untouched, tax
  bit-identical (its test is the physical regression guard: 26.65→2.66).

Anti-plans:
- 4-5 micro-tasks (flagship).
- "Refactor rules.py into a per-domain rounding policy framework" (scope
  bait: pricing.py/reports.py/batching.py in must_not_expand).
- Changing DEFAULT_MODE instead of pinning modes at the call sites (would
  silently flip tax → caught by the unchanged-TestTax requirement; plan
  level: the freeze note says default stays).
- Forgetting that inventory must pass the mode EXPLICITLY even though the
  value doesn't change (final_acceptance markers: HALF_EVEN / explicit).
