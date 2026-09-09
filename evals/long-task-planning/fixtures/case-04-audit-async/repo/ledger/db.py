"""Minimal dict-based persistence store."""


class Store:
    """Tables of records; records are dicts."""

    def __init__(self):
        self._tables = {}

    def insert(self, table, record):
        self._tables.setdefault(table, []).append(dict(record))
        return record

    def find(self, table, **fields):
        out = []
        for rec in self._tables.get(table, []):
            if all(rec.get(k) == v for k, v in fields.items()):
                out.append(rec)
        return out

    def all(self, table):
        return list(self._tables.get(table, []))
