"""Append-only event log."""


class EventLog:
    def __init__(self):
        self._events = []

    def record(self, event):
        self._events.append(dict(event))
        return event

    def events(self):
        return [dict(e) for e in self._events]
