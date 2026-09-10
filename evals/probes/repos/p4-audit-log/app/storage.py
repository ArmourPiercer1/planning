"""Fixed-capacity ring buffer storage.

Platform constraint: exactly one store instance may exist; the buffer
overwrites the oldest slot when full. Do not add a second store.
"""
from __future__ import annotations


class RingBuffer:
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._slots: list[dict | None] = [None] * capacity
        self._head = 0  # next slot to overwrite
        self._count = 0

    def append(self, item: dict) -> None:
        self._slots[self._head] = item
        self._head = (self._head + 1) % self.capacity
        self._count = min(self._count + 1, self.capacity)

    def read_all(self) -> list[dict]:
        if self._count < self.capacity:
            return list(self._slots[: self._count])
        # full: oldest is at _head
        return list(self._slots[self._head:] + self._slots[: self._head])

    def __len__(self) -> int:
        return self._count
