"""Request handlers for the ledger service."""

import datetime as _dt

# Audit event wire format — existing downstream consumers read exactly these
# fields. Keep backward compatible.
AUDIT_EVENT_FIELDS = ("ts", "actor", "action", "entity", "amount")
AUDIT_TOPIC = "audit"


def _now():
    return _dt.datetime.utcnow().isoformat() + "Z"


def handle_transfer(store, bus, from_id, to_id, amount):
    """Move funds between accounts and record the audit event.

    Current behavior: the audit event is persisted synchronously into the
    'audit' table as part of the request (legacy path).
    """
    if amount <= 0:
        return {"ok": False, "error": "bad-amount"}
    store.insert("transactions", {"from": from_id, "to": to_id, "amount": amount, "ts": _now()})
    # legacy: synchronous audit persistence in the request path
    store.insert("audit", {
        "ts": _now(),
        "actor": from_id,
        "action": "transfer",
        "entity": to_id,
        "amount": amount,
    })
    return {"ok": True}
