"""Durable JSON file queue (one file per queue; V1 simplicity)."""

import json
import os


class JsonQueue:
    """A minimal durable queue of JSON-serializable records.

    Records are dicts; 'pending' means status != 'sent' (see usage in
    notify/cli.py). The file is rewritten on each mutation, which is
    acceptable at this scale.
    """

    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([], fh)

    def _load(self):
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, items):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=1)

    def enqueue(self, item):
        items = self._load()
        items.append(item)
        self._save(items)
        return item

    def pending(self):
        return [m for m in self._load() if m.get("status") != "sent"]

    def mark_done(self, item_id):
        items = self._load()
        for m in items:
            if m.get("id") == item_id:
                m["status"] = "sent"
        self._save(items)

    def all(self):
        return self._load()
