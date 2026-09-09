"""Spool writer backends.

Contract (shared by all backends): a writer exposes append(event) and
close(). Events are JSON-serializable dicts. The file backend writes one
JSON object per line (JSONL).
"""

import json
import os

from spool import config as _config


class FileSpoolWriter:
    def __init__(self, path):
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def append(self, event):
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")

    def close(self):
        pass  # V1: nothing to release


def open_writer(cfg=None):
    """Factory: backend selection by cfg['spool_backend'].

    Currently only 'file' is implemented; 'memory' is the planned test
    backend (not yet implemented).
    """
    cfg = cfg or _config.get_config()
    if cfg["spool_backend"] == "file":
        return FileSpoolWriter(cfg["spool_path"])
    raise ValueError(f"unknown spool backend: {cfg['spool_backend']}")
