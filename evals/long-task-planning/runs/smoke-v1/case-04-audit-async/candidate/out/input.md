# Verbatim task

# Task: async audit logging

Today `handle_transfer` in `ledger/api.py` persists the audit event
synchronously (it inserts straight into the `audit` table inside the
request). We want audit logging decoupled from the request path:

1. The API handler must **publish** the audit event on the bus (topic
   `AUDIT_TOPIC = "audit"`, format `AUDIT_EVENT_FIELDS` — see
   `ledger/api.py`) instead of writing to the store itself. The handler's
   response must not depend on audit persistence succeeding.
2. A **worker** must consume the `audit` topic and persist events to the
   `audit` table. Use the existing consumer in `ledger/worker.py`
   (`make_audit_consumer`) or extend it — it already dedupes
   re-deliveries (at-least-once safety), which must be preserved.
3. The audit event format (fields, topic name) must stay backward
   compatible: existing downstream consumers read exactly
   `{ts, actor, action, entity, amount}`.
4. The `transactions` write in `handle_transfer` must happen exactly as
   before.

All existing tests must keep passing (they test current behavior — adjust
them only where the task explicitly changes the flow, e.g. audit now lands
via the bus; add tests for the new publish/consume path, including the
dedupe behavior at the bus level).

The repo layout:

```
ledger/
  __init__.py
  db.py        # Store: insert / find / all
  events.py    # Bus: subscribe / publish
  api.py       # handle_transfer, AUDIT_EVENT_FIELDS, AUDIT_TOPIC
  worker.py    # make_audit_consumer(store)
tests/
  test_ledger.py
```

# Repo notes (bounded scan)

Layer map (all files small, ~20–60 lines):

| File | Layer | Responsibility |
|---|---|---|
| `ledger/api.py` | api | `handle_transfer(store, bus, from_id, to_id, amount)`; constants `AUDIT_EVENT_FIELDS = ("ts","actor","action","entity","amount")`, `AUDIT_TOPIC = "audit"`; currently inserts the audit row synchronously (legacy path) |
| `ledger/events.py` | runtime | in-process `Bus`: `subscribe(topic, fn)`, `publish(topic, event)`; handlers run in subscription order; **V1: subscriber exceptions propagate to the publisher (no isolation)** |
| `ledger/db.py` | persistence | dict-based `Store`: `insert`, `find`, `all` |
| `ledger/worker.py` | runtime | `make_audit_consumer(store)` → `consume(event)`; dedupes on `(ts, actor, action)` via `store.find` before `store.insert` |
| `tests/test_ledger.py` | e2e/unit | unittest (stdlib `unittest.TestCase`), all green: TestStore, TestBus, TestApi (2 tests), TestWorker (1 test) |

Known traps:

- `TestApi.test_transfer_ok_and_audit_written` asserts the synchronous audit row — it tests the exact behavior this task changes, so it is the only existing test that must be adjusted (task says: adjust where the flow changes).
- `Bus` V1 has no subscriber isolation: to make the handler's response independent of audit persistence, isolation must live in the handler (the bus is frozen read-only).
- Dedup key is `(ts, actor, action)` — not the full event dict.
- No app entrypoint/lifespan exists in the fixture; consumer wiring happens at the call/test level (`bus.subscribe(AUDIT_TOPIC, make_audit_consumer(store))`).
- Test style: stdlib `unittest`, no pytest, no third-party dependencies anywhere.
