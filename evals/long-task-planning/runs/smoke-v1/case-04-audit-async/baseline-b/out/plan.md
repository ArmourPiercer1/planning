# Plan: Async audit logging for the ledger service

**Task:** decouple audit logging from the request path in `handle_transfer`
(`ledger/api.py`) — the handler publishes the audit event on the bus instead of
writing the `audit` table itself, and a worker consumes the `audit` topic and
persists the events.

**Repo under work** (read-only for this plan): `ledger/{__init__,db,events,api,worker}.py`,
`tests/test_ledger.py`.

## Current state (established by code reading)

- `handle_transfer(store, bus, from_id, to_id, amount)` validates the amount,
  inserts into `transactions`, then **synchronously** inserts into `audit`, and
  returns `{"ok": True}`. The `bus` argument is already threaded through but
  unused.
- `Bus` (`ledger/events.py`) is a synchronous in-memory pub/sub: `publish`
  invokes subscribers in subscription order, and a raising subscriber
  **propagates to the publisher** (documented V1 behavior, no isolation).
- `make_audit_consumer(store)` (`ledger/worker.py`) persists an audit event and
  dedupes re-deliveries by looking up `(ts, actor, action)` in the `audit`
  table — at-least-once safe. This dedupe logic must be preserved as-is.
- `Store` (`ledger/db.py`) is a dict-based in-memory store with
  `insert` / `find` / `all`.
- Wire format constants `AUDIT_EVENT_FIELDS = ("ts","actor","action","entity","amount")`
  and `AUDIT_TOPIC = "audit"` live in `ledger/api.py` and must stay
  backward compatible.

## Design decisions (frozen before implementation)

- **D1 — "async" means pub/sub decoupling, not new concurrency.** The existing
  in-memory `Bus` is used unchanged; no threads, queues, or background process
  are introduced.
- **D2 — Producer change.** In `handle_transfer`, replace the direct
  `store.insert("audit", …)` with `bus.publish(AUDIT_TOPIC, event)`. The event
  dict carries exactly the `AUDIT_EVENT_FIELDS` keys
  (`ts=_now(), actor=from_id, action="transfer", entity=to_id, amount=amount`)
  and the topic name stays `"audit"`.
- **D3 — Guard the publish so the response cannot depend on audit persistence.**
  `bus.publish` propagates subscriber exceptions, so a failing consumer would
  otherwise turn `handle_transfer` into a 500-ish failure. Wrap the publish in
  `try/except`, log the exception, and keep the response `{"ok": True}`.
  Rationale: this is the minimal change that satisfies "the handler's response
  must not depend on audit persistence succeeding" without altering `Bus`
  semantics for all topics (bus-level isolation is the rejected alternative —
  it changes shared infrastructure for every topic to fix one producer).
  Known consequence: in V1 a failed consumer means the event is not retried
  (logged, dropped). That is acceptable per task; retries are out of scope.
- **D4 — Wiring point.** Add a small helper in `ledger/worker.py`,
  `attach_audit_consumer(store, bus)`, which does
  `bus.subscribe(AUDIT_TOPIC, make_audit_consumer(store))`. The repo has no
  service entry point, so tests are the primary composition site; the helper
  keeps that one line identical everywhere. Fallback if the helper is judged
  extra surface: subscribe inline in each test.
- **D5 — `transactions` write untouched.** Same table, same record fields
  (`from`, `to`, `amount`, `ts`), same position (after validation). The
  `store` parameter remains in use for it.
- **D6 — Consumer internals untouched.** `make_audit_consumer` keeps its
  `(ts, actor, action)` dedupe lookup exactly as written.

## Phases

### Phase 1 — Baseline (rationale: establish a green starting point so any later
failure is provably caused by this change)

- [ ] Run the existing suite from the repo root
      (`python -m unittest discover -s tests -v`; the repo uses stdlib
      `unittest`) and record the result as the green baseline.
- [ ] Note current observable behavior: bad-amount requests write neither a
      `transactions` row nor an `audit` row.

### Phase 2 — Consumer side: make the audit sink available on the bus
(rationale: the sink must exist before the producer stops writing directly, so
there is no window in which audit events are published to a topic nobody
consumes — the bus has no store-and-forward, so an un-subscribed topic drops
events)

- [ ] Add `attach_audit_consumer(store, bus)` to `ledger/worker.py`
      (subscribes `make_audit_consumer(store)` to `AUDIT_TOPIC` per D4).
- [ ] Verify `make_audit_consumer` is otherwise byte-for-byte unchanged
      (dedupe by `ts`+`actor`+`action` preserved per D6).

### Phase 3 — Producer side: publish instead of direct write
(rationale: once a consumer is available, flip the handler so the request path
no longer touches the `audit` table)

- [ ] In `handle_transfer`, delete the legacy `store.insert("audit", …)` block.
- [ ] Build the audit event with exactly the `AUDIT_EVENT_FIELDS` keys
      (`ts` from a fresh `_now()` call, as today) and call
      `bus.publish(AUDIT_TOPIC, event)`.
- [ ] Wrap the publish in `try/except` with logging, response unchanged (D3).
- [ ] Confirm the `transactions` insert is byte-for-byte the same as before,
      still after the amount validation and still before the response (D5).

### Phase 4 — Tests (rationale: the task explicitly changes where audit rows
come from, so the one test asserting the old flow must be adjusted, and the
new publish/consume behavior — including bus-level dedupe — needs coverage)

- [ ] Adjust `TestApi.test_transfer_ok_and_audit_written`: wire the bus
      (`attach_audit_consumer(store, bus)`) so the audit row now lands via the
      worker; keep the existing assertions on row count, key set
      (`set(AUDIT_EVENT_FIELDS)`), and `action == "transfer"`.
- [ ] Add `test_handler_publishes_audit_event_on_bus`: subscribe a spy on
      `AUDIT_TOPIC`, call `handle_transfer`, assert the event's key set equals
      `set(AUDIT_EVENT_FIELDS)` and the values are correct.
- [ ] Add end-to-end test: `attach_audit_consumer(store, bus)` +
      `handle_transfer` → response `{"ok": True}`, exactly one `audit` row
      written by the worker, one `transactions` row.
- [ ] Add bus-level dedupe test: with the consumer subscribed, publish the same
      event (same `ts`/`actor`/`action`) twice on the `audit` topic → exactly
      one `audit` row, second consume reports `deduped`.
- [ ] Add decoupling test: a subscriber that raises → `handle_transfer` still
      returns `{"ok": True}` and the `transactions` row is still written
      (exercises D3).
- [ ] Keep `test_bad_amount_rejected` (no audit row) and `TestWorker`
      (direct consumer dedupe) as-is; optionally extend the bad-amount test to
      also assert no `transactions` row.

### Phase 5 — Verification (rationale: prove the invariants the task freezes —
wire format, topic, dedupe, decoupling, unchanged `transactions` — and that
nothing outside the three intended files moved)

- [ ] Run the full suite (old + new tests); all green.
- [ ] Backward-compat check: `AUDIT_TOPIC` and `AUDIT_EVENT_FIELDS` values
      unchanged; grep confirms no `store.insert("audit", …)` remains in the
      request path (worker is the only audit writer).
- [ ] Diff review: only `ledger/api.py`, `ledger/worker.py`,
      `tests/test_ledger.py` changed.

## Implementation checklist (explicit step order)

1. Run baseline test suite; record green.
2. Add `attach_audit_consumer(store, bus)` in `ledger/worker.py`.
3. In `ledger/api.py`, replace the direct audit insert with a guarded
   `bus.publish(AUDIT_TOPIC, event)`; leave the `transactions` insert untouched.
4. Adjust `test_transfer_ok_and_audit_written` to wire the audit consumer onto
   the bus.
5. Add the four new tests (publish format, end-to-end, bus-level dedupe,
   decoupling under a failing consumer).
6. Run the full test suite; all green.
7. Backward-compat + diff review.

**Dependencies (prose):**

- **Step 3 happens after step 2** because the `Bus` has no queue or
  store-and-forward: if the producer switched to publish-only before any
  consumer was attached to the `audit` topic, every audit event would be
  silently dropped, and the adjusted tests (step 4) would see zero audit rows.
- **Step 4 happens immediately after step 3** (and not earlier as a committed
  change) because that test asserts the audit row exists after
  `handle_transfer` returns; without the producer change it would be testing
  the legacy path, and with the producer change but without the bus wiring it
  would fail. Changing producer and test together keeps the tree consistent at
  each step. (Writing step 4 first in TDD style is acceptable; committing it
  before step 3 is not.)
- **Step 5 happens after steps 3 and 4** because all four new tests exercise
  the publish→consume path, which only exists once both the producer publishes
  (step 3) and the wiring helper exists (step 2); the decoupling test
  specifically depends on the guard added in step 3.
- **Step 6 happens after steps 1–5** because it is the gate that compares the
  new behavior against the baseline recorded in step 1; running it earlier
  would only measure a half-converted system.
- **Step 7 happens after step 6** because it is a review pass over the final
  diff; doing it before the suite is green would review code still in flux.

## Testing & verification

- **Command:** from the repo root,
  `python -m unittest discover -s tests -v` (stdlib `unittest`; no external
  dependencies). No test requires network or a real database.
- **Inventory:** 6 existing tests (1 `TestStore`, 2 `TestBus`, 2 `TestApi`,
  1 `TestWorker` — adjusted: `test_transfer_ok_and_audit_written`) plus 4 new
  tests in `TestApi` (publish format, end-to-end, bus-level dedupe,
  decoupling under a failing consumer).
- **Invariants to verify:**
  1. Bad amount → `{"ok": False, "error": "bad-amount"}`, no `transactions`
     row, no `audit` row, nothing published.
  2. Valid transfer → `{"ok": True}`, exactly one `transactions` row with the
     same record shape as before.
  3. Audit event on topic `"audit"` has exactly the keys
     `{ts, actor, action, entity, amount}` — nothing added, nothing dropped
     (backward compatibility for downstream consumers).
  4. Re-delivery of an event with the same `(ts, actor, action)` at the bus
     level produces no second `audit` row (at-least-once safety preserved).
  5. A consumer that raises does not change the `handle_transfer` response and
     does not affect the `transactions` write.
- **Regression check:** the pre-existing `TestWorker` test (direct consumer
  dedupe) must pass unchanged, proving the consumer's dedupe was not altered.
- **Rollback:** revert the three-file diff (`ledger/api.py`,
  `ledger/worker.py`, `tests/test_ledger.py`); baseline from step 1 is the
  acceptance reference.

## Out of scope

- True asynchrony: threads, task queues, background processes, or any change
  to the in-memory `Bus`'s synchronous, in-order delivery.
- Changing `Bus` semantics for other topics (isolation, ordering, retries,
  acks); only the handler-side guard (D3) touches failure behavior.
- Retries, backoff, or dead-letter handling for lost audit events; in V1 a
  consumer exception during a request means the event is logged and dropped.
- Any change to `Store` (persistence engine, real DB, durability).
- Audit events for actions other than `transfer`; no new topics or event
  fields.
- Any change to the API response shapes (`{"ok": True}` /
  `{"ok": False, "error": "bad-amount"}`) or to the `transactions` record
  format.
- The existing dedupe-key collision window (two distinct transfers sharing
  `ts`+`actor`+`action`) — pre-existing consumer behavior, unchanged by
  design.
- Migration or backfill of existing `audit` rows.
