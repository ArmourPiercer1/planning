# case-05 — trap documentation (NEVER shown to planning subagents)

**Type E — hidden integration seam.** Both sides of the boundary are unit-
green today:

- `bank/api.py` — real shape: `{"items": [...], "next_cursor": ...}`.
- `bank/views.py` — ships a **draft** helper `_iter_api_page` that assumes
  `{"results": [...], "cursor": ...}` and a test that pins that wrong
  assumption (`test_draft_page_helper_uses_assumed_shape`).

A plan that splits "view work" and "API understanding" into independent
leaves, each validated by its own unit tests, misses the seam: the e2e path
(view → real API) fails on the key mismatch. The task explicitly forbids
changing `bank/api.py`, so the only legal fix is view-side adaptation +
correcting/removing the draft assumption.

Ground truth:
- `must_freeze A1 contract`: the REAL shape is canonical.
- `must_freeze A3 contract`: the txn model fields.
- Gates: a `contract_consistency` gate (keys: results/items/cursor/shape/
  draft) and an `e2e_closure` gate (pagination + shape), both covering the
  real API.
- Cap 1 anchor/task: a blob that owns both api.py and views.py is the
  seam-hiding anti-plan.
- Range [2, 5]: view implementation + multi-page e2e test (+ optionally a
  draft-correction task) is the expected shape.

Traps:
- "Adapt the API to the draft" (contract flip — the task forbids it).
- Unit-testing `statement_for` with hand-built pages in the wrong shape
  (passes locally, e2e still broken — the gate requirement targets exactly
  this).
- Invented scope: reports, emails, rate limits.
