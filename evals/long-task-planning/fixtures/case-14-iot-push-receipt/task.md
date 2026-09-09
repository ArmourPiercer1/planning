# Task: observable device pushes (receipts + event log)

The push gateway is fire-and-forget: `Gateway.push(payload)` returns
`None` and failures (unknown device, ...) are invisible except in the
module-level `EVENTS` list. Make pushes observable:

1. **Receipts.** `Gateway.push` must return a delivery receipt
   `{"device_id": str, "accepted": bool, "error": str | None}` —
   `accepted=True` with `error=None` on success; `accepted=False` with a
   human-readable `error` (e.g. the unknown-device reason) on rejection.
   Existing internal call sites call `push()` and **ignore the return
   value** — they must keep working (returning a receipt is compatible
   with callers that discard it).
2. **Event log.** The event log (`iot/store.py`, class `EventLog`) must
   record **both** accepted and rejected pushes, with the reason. The
   gateway needs access to an `EventLog` (constructor parameter is fine).
3. **Legacy path untouched.** Devices on the 2019 firmware keep using the
   legacy wire format (`iot/legacy_format.py`). That module and its
   behavior are out of scope — no changes, no deprecation work.
4. The device registry semantics (`iot/devices.py`) must not change.

All existing tests must keep passing (update the two `push` tests that pin
the V1 no-receipt behavior to pin the new receipt behavior); add tests for
the receipt shape, rejection reasons, event-log coverage, and
call-site compatibility (ignoring the return value still works).

Repo layout:

```
iot/
  __init__.py
  devices.py       # get_device, is_legacy, LEGACY_FIRMWARE
  gateway.py       # Gateway.push (V1: -> None, EVENTS list)
  store.py         # EventLog: record / events
  legacy_format.py # format_legacy — 2019 firmware, LEGACY
tests/
  test_iot.py
```
