# Plan: Async audit logging for the ledger service

## 1. Task restatement (from `task.md`)

Move audit logging out of the request path:

- **R1** — `handle_transfer` must **publish** the audit event on the bus (topic `AUDIT_TOPIC = "audit"`, wire format `AUDIT_EVENT_FIELDS`) instead of inserting into the `audit` table itself. The handler's response must **not** depend on audit persistence succeeding.
- **R2** — A worker must consume the `audit` topic and persist events to the `audit` table, using or extending the existing `ledger/worker.py::make_audit_consumer`. Its dedupe behavior (at-least-once safety) must be preserved.
- **R3** — The audit event format (fields, topic name) stays backward compatible: downstream consumers read exactly `{ts, actor, action, entity, amount}`.
- **R4** — The `transactions` write in `handle_transfer` happens exactly as before.
- **Tests** — all existing tests keep passing, adjusted only where the flow explicitly changes (audit now lands via the bus); add tests for the new publish/consume path, including dedupe at the bus level.

## 2. Current state (what I read in the repo)

| File | Contents relevant to this task |
|---|---|
| `ledger/db.py` | `Store`: in-memory dict tables; `insert` / `find(**fields)` / `all`. No schema enforcement. |
| `ledger/events.py` | `Bus`: synchronous pub/sub. Subscribers run in subscription order. **A subscriber that raises propagates to the publisher — no isolation in V1.** |
| `ledger/api.py` | `handle_transfer(store, bus, from_id, to_id, amount)`: rejects `amount <= 0`; inserts a `transactions` row; then **synchronously inserts the audit row** (the legacy path to be removed). Exports `AUDIT_EVENT_FIELDS = ("ts", "actor", "action", "entity", "amount")` and `AUDIT_TOPIC = "audit"`. `_now()` = `datetime.utcnow().isoformat() + "Z"`. |
| `ledger/worker.py` | `make_audit_consumer(store)` returns a handler that dedupes on **`(ts, actor, action)`** (via `store.find`) and otherwise persists the event. This dedupe key is the at-least-once safety net — keep it. |
| `tests/test_ledger.py` | 6 tests. Two touch the audit flow: `test_transfer_ok_and_audit_written` (asserts an audit row lands **directly** in the store from an *unwired* bus — will break once the handler publishes) and `test_bad_amount_rejected` (asserts no audit row — still valid). `test_audit_consumer_persists_and_dedupes` covers the consumer's dedupe directly. |

Key observation: the repo has **no process entry point / no threads / no queue** — the `Bus` is the seam. "Async" here means *decoupled via the bus*, not adding a worker thread or a queue implementation.

## 3. Design decisions

- **D1 — Handler publishes, store untouched.** In `handle_transfer`, replace the legacy `store.insert("audit", ...)` with `bus.publish(AUDIT_TOPIC, event)` where `event` is a dict with **exactly** the five `AUDIT_EVENT_FIELDS` keys (`ts`, `actor=from_id`, `action="transfer"`, `entity=to_id`, `amount`). No extra fields: `test_transfer_ok_and_audit_written` asserts `set(row.keys()) == set(AUDIT_EVENT_FIELDS)` and the consumer persists `dict(event)` verbatim, so any extra key would land in the table and break R3.
- **D2 — Handler is insulated from audit failures.** Because `Bus.publish` propagates subscriber exceptions, a failing consumer would otherwise fail the transfer, violating R1. So the handler wraps the publish in `try/except Exception` and continues (comment: audit is best-effort in V1; a dead-letter hook is a future improvement). Order is preserved: `transactions` insert happens **before** the publish, and the rejection path (`amount <= 0`) returns before publishing anything.
- **D3 — Worker: reuse the existing consumer, add a wiring helper.** `make_audit_consumer` stays unchanged (its `(ts, actor, action)` dedupe is the preserved at-least-once semantics). Add a one-line `connect_audit_worker(store, bus)` to `ledger/worker.py` that does `bus.subscribe(AUDIT_TOPIC, make_audit_consumer(store))`. `worker.py` imports `AUDIT_TOPIC` from `ledger.api` — no circular import, since `api.py` does not import `worker`. This gives tests and any future composition a single, explicit wiring point (the repo has no app main to hang wiring on).
- **D4 — Nothing else changes.** `Store`, `Bus`, the event field set, the topic name, `_now()` format, and the dedupe key are all untouched. No threads, no queue, no new dependencies, no logging infrastructure — the synchronous in-memory bus keeps tests deterministic; a real queue-backed bus later delivers at-least-once, which is exactly where the preserved dedupe pays off.

## 4. Step-by-step implementation

**Step 1 — `ledger/api.py` (the core change)**
1. Delete the legacy `store.insert("audit", {...})` block.
2. Build the event dict with exactly the five fields (same values as today: `ts=_now()`, `actor=from_id`, `action="transfer"`, `entity=to_id`, `amount=amount`).
3. `bus.publish(AUDIT_TOPIC, event)` inside `try/except Exception: pass` (documented swallow; see D2).
4. Update the docstring: audit is now published on the bus and persisted by the audit worker; the response does not depend on audit persistence.

**Step 2 — `ledger/worker.py`**
Add:
```python
from ledger.api import AUDIT_TOPIC

def connect_audit_worker(store, bus):
    """Wire the audit consumer to the bus (explicit composition point)."""
    bus.subscribe(AUDIT_TOPIC, make_audit_consumer(store))
```

**Step 3 — `tests/test_ledger.py`**
- *Adjust* (only the flow change the task names): `test_transfer_ok_and_audit_written` — wire `connect_audit_worker(store, bus)` before calling `handle_transfer`. The in-memory bus is synchronous, so the audit row still lands during the call and the existing assertions (one row, exact field set, `action == "transfer"`) hold.
- *Add*:
  1. `test_transfer_publishes_audit_event_on_bus` — spy subscriber on `AUDIT_TOPIC`; assert one publish with exactly the `AUDIT_EVENT_FIELDS` keys and correct values (`actor` = from, `entity` = to, amount echoed).
  2. `test_transfer_ok_when_audit_persistence_fails` — subscribe a handler that raises; `handle_transfer` still returns `{"ok": True}` and the `transactions` row is still written (R1 + R4 together).
  3. `test_bus_level_dedupe_on_redelivery` — wire the real consumer; publish the same event twice (simulating at-least-once replay) → exactly 1 audit row; publish a distinct event → 2 rows (R2, bus-level dedupe).
  4. `test_bad_amount_publishes_nothing` — spy subscriber records zero publishes for a rejected transfer (pairs with the existing `test_bad_amount_rejected`, which continues to pass unchanged).
  5. `test_transactions_write_unchanged` — assert the `transactions` row fields (`from`, `to`, `amount`, `ts`) exactly as before (R4, which no existing test covers).

**Step 4 — Run the full suite** (see §5).

Files changed: `ledger/api.py`, `ledger/worker.py`, `tests/test_ledger.py`.
Files intentionally untouched: `ledger/db.py`, `ledger/events.py`, `ledger/__init__.py`.

## 5. Verification

- From the repo root: `python -m unittest discover -v` (stdlib `unittest`; no new dependencies). Equivalent: `python -m unittest tests.test_ledger -v`.
- Expected: the 6 pre-existing tests (one adjusted as above, the rest unchanged — including `test_bad_amount_rejected`, `test_audit_consumer_persists_and_dedupes`, and all `Store`/`Bus` tests) plus 5 new tests = **11 tests, all green**.
- Manual spot-check: with the consumer wired, a transfer yields exactly one `audit` row (deduped on replay) and exactly one `transactions` row.

## 6. Risks and edge cases

- **Dedupe-key collisions** — the preserved key is `(ts, actor, action)`, so two different transfers from the same actor in the same microsecond would dedupe to one row. This is *pre-existing* consumer semantics; changing the key is out of scope and could break replay expectations. Note it, don't fix it.
- **Lost audit events on failure** — the `try/except` in the handler means an audit failure is swallowed (event lost, no retry queue in V1). Accepted by R1 (response must not depend on audit persistence); document the dead-letter hook as the next step.
- **Subscriber-order sensitivity** — `Bus` runs subscribers in subscription order and propagates exceptions; if other `audit` subscribers exist downstream, a failing *non-audit* subscriber is also shielded from the handler by D2 (the contract is about the response, and D2 covers it wholesale).
- **Backward compatibility** — do not rename, reorder, or add event fields, and do not rename `AUDIT_TOPIC`; downstream consumers read exactly the current shape.
- **Over-engineering trap** — adding threads/queues here would make tests nondeterministic and touch `Bus`; the bus seam is the right V1 boundary.
- `datetime.utcnow()` deprecation is pre-existing and out of scope (changing the `ts` format would break R3).

## 7. Non-goals

- No changes to `Store` or `Bus` internals.
- No worker threads, queues, or retry/dead-letter infrastructure (future work).
- No new dependencies, no logging framework, no schema/migration changes.
