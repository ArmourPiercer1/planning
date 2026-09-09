"""Ledger API: add and list transactions with cursor pagination."""

from bank.models import make_txn


class Ledger:
    """In-memory ledger with cursor-paginated listings."""

    def __init__(self, txns=None):
        self._txns = list(txns or [])
        self._next_id = 1

    def add(self, user, date, amount, kind="credit"):
        txn = make_txn(f"t{self._next_id}", user, date, amount, kind)
        self._next_id += 1
        self._txns.append(txn)
        return txn

    def list_transactions(self, user, cursor=None, limit=20):
        """Paginated listing for one user, oldest first.

        Returns {"items": [txn, ...], "next_cursor": str | None}.
        The cursor is the stringified offset after the last returned item;
        pass it back as `cursor` to get the next page.
        """
        rows = [t for t in self._txns if t["user"] == user]
        start = int(cursor) if cursor else 0
        page = rows[start:start + limit]
        end = start + len(page)
        next_cursor = str(end) if end < len(rows) else None
        return {"items": page, "next_cursor": next_cursor}
