"""Background workers: consume bus topics and persist to the store."""


def make_audit_consumer(store):
    """Return a handler for the 'audit' topic that persists the event.

    Persistence is idempotent: re-delivering the same event (same
    ts+actor+action) does not create a second row, so at-least-once
    delivery is safe.
    """

    def consume(event):
        dup = store.find("audit", ts=event.get("ts"), actor=event.get("actor"),
                         action=event.get("action"))
        if dup:
            return {"ok": True, "deduped": True}
        store.insert("audit", dict(event))
        return {"ok": True, "deduped": False}

    return consume
