"""In-memory event bus (pub/sub by topic)."""


class Bus:
    """Publish/subscribe bus. Handlers run in subscription order."""

    def __init__(self):
        self._subs = {}

    def subscribe(self, topic, fn):
        self._subs.setdefault(topic, []).append(fn)

    def publish(self, topic, event):
        """Publish an event dict to all subscribers of the topic.

        Returns the event for convenience. Subscribers that raise propagate
        to the publisher (no isolation in V1).
        """
        for fn in list(self._subs.get(topic, [])):
            fn(event)
        return event
