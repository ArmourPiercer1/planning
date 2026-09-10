"""Config store tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.config_store import ConfigError, JsonConfigStore
from app.loader import load_config

VALID = {"app_name": "svc", "env": "test", "log_level": "info"}


class TestConfigStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.json"
        self.path.write_text(json.dumps(VALID), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_set_roundtrip(self):
        store = JsonConfigStore(self.path)
        store.set("feature_x", True)
        again = JsonConfigStore(self.path)
        self.assertTrue(again.get("feature_x"))

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            JsonConfigStore(Path(self.tmp.name) / "nope.json")

    def test_loader_validates(self):
        data = load_config(self.path)
        self.assertEqual(data["app_name"], "svc")
        bad = dict(VALID, log_level="verbose")
        self.path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(self.path)


if __name__ == "__main__":
    unittest.main()
