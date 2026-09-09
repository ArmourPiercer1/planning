"""Domain models (plain dicts for V1)."""

TXN_FIELDS = ("id", "user", "date", "amount", "kind")


def make_txn(txn_id, user, date, amount, kind="credit"):
    return {"id": txn_id, "user": user, "date": date, "amount": amount, "kind": kind}
