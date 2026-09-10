# todosvc (probe fixture)

A small todo service. Stage 1 of this engagement (adding list filtering)
is **already complete** — its planning artifacts are in `stage-1/`
(stage-contract, task checkpoints, stage-checkpoint). Stage 2 planning
happens on top of them.

## Layout

- `app/api.py` — endpoint handlers (`GET /todos`, `POST /todos`,
  `POST /todos/{id}/done`).
- `app/store.py` — in-memory store.
- `app/webhooks.py` — existing webhook dispatch infra (fire-and-forget;
  `send(url, payload)` returns the HTTP status; failures are logged,
  never raised).
- `tests/test_api.py` — the suite that must stay green.
- `stage-1/` — the completed stage-1 planning artifacts (READ these
  before planning stage 2; they are the frozen baseline).

## Platform notes

- Python 3.11, stdlib only.
- The stage-1 contract is frozen: its shared contracts and out-of-scope
  list are the baseline for stage 2. Stage 2 may extend, but any change
  to a frozen item is drift and must be surfaced, not absorbed silently.
