"""In-memory todo store."""
from __future__ import annotations


class TodoStore:
    def __init__(self):
        self._todos: list[dict] = []

    def add(self, todo: dict) -> None:
        self._todos.append(todo)

    def get(self, todo_id: str) -> dict | None:
        return next((t for t in self._todos if t["id"] == todo_id), None)

    def all(self) -> list[dict]:
        return [dict(t) for t in self._todos]
