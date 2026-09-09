# case-03 — trap documentation (NEVER shown to planning subagents)

**Type C — fake parallelism.** "Bulk discount" and "loyalty program" read as
two independent features → the naive plan runs two parallel tasks. The catch:
both features mutate the **same** artifact — the `default_registry()` list in
`shop/discounts.py` — and the loyalty rule additionally needs the tier context
from `shop/loyalty.py`.

Ground truth:
- `forbidden_parallel_pairs: [A2, A3]` on `shop/discounts.py`: if the plan
  has an unordered pair of tasks that both OWN `shop/discounts.py` (e.g. a
  bulk task + a loyalty task), it is a hazardous ownership collision.
  Serializing the two is legal (ordered pair passes); merging them into one
  rule-addition closure is the best answer.
- `context_clusters: merge [A2, A3]`: the two rules + tier lookup are one
  small closure (3 files, all tiny).
- `must_freeze A1 behavior`: multiply-all + round-once-at-end. A plan that
  leaves rounding semantics implicit (or lets a rule task "improve" rounding
  per rule) misses the behavior freeze.
- Range [2, 4], cap 2: the expected shape is ~2-3 tasks (one rule closure +
  an e2e/composition test, or split engine-contract/rule-work).

Traps:
- Two parallel rule tasks both owning discounts.py → G-collision + pair
  violation (the flagship trap).
- Invented scope: payments, tax, a promotions framework (must_not_expand).
- Treating `loyalty.py` as work when `get_tier` already exists — it is
  context, not a change target (a task that owns only loyalty.py and does
  nothing is fine-grain over-splitting; the scorer's task count + cluster
  checks catch extremes).
