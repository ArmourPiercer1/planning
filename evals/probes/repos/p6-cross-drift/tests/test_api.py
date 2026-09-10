"""API tests (stage-1 frozen suite)."""
from __future__ import annotations

import unittest

from app.api import TodoAPI
from app.store import TodoStore


class TestTodos(unittest.TestCase):
    def setUp(self):
        self.api = TodoAPI(TodoStore())

    def test_create_and_list_shape(self):
        _, created = self.api.create_todo({"title": "buy milk"})
        status, body = self.api.list_todos({})
        self.assertEqual(status, 200)
        self.assertEqual(set(body["todos"][0].keys()), {"id", "title", "done"})

    def test_mark_done(self):
        _, created = self.api.create_todo({"title": "x"})
        status, body = self.api.mark_done({"id": created["id"]}, {})
        self.assertEqual(status, 200)
        self.assertTrue(body["done"])

    def test_mark_done_unknown(self):
        status, _ = self.api.mark_done({"id": "nope"}, {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
