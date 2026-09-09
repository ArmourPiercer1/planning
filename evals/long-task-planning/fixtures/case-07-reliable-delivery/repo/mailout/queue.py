"""Simple FIFO message queue."""


class MessageQueue:
    def __init__(self, messages=None):
        self._items = list(messages or [])

    def put(self, msg):
        self._items.append(dict(msg))

    def get(self):
        return self._items.pop(0)

    def qsize(self):
        return len(self._items)
