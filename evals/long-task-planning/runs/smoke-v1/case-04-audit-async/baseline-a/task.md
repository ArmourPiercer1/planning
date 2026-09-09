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
