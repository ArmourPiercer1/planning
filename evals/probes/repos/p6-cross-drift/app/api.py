"""Todo API handlers."""
from __future__ import annotations

from .store import TodoStore

_next_id = 0


class TodoAPI:
    def __init__(self, store: TodoStore | None = None):
        self.store = store or TodoStore()

    def list_todos(self, body: dict) -> tuple[int, dict]:
        """GET /todos — response shape is FROZEN (stage 1, contract C1)."""
        return 200, {"todos": self.store.all()}

    def create_todo(self, body: dict) -> tuple[int, dict]:
        global _next_id
        _next_id += 1
        todo = {"id": f"t{_next_id}", "title": body.get("title", ""), "done": False}
        self.store.add(todo)
        return 201, {"id": todo["id"]}

    def mark_done(self, path_params: dict, body: dict) -> tuple[int, dict]:
        todo = self.store.get(path_params["id"])
        if todo is None:
            return 404, {"error": "unknown todo"}
        todo["done"] = True
        return 200, {"id": todo["id"], "done": True}
