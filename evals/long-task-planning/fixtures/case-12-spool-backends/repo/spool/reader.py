"""Spool reader backends.

Contract (shared by all backends): a reader exposes read_all(),
read_from(offset), offset_of_last(), and truncate().

IMPORTANT: for the file backend, offsets are BYTE offsets into the spool
file; callers persist offsets between polls and pass them back to
read_from. Any other backend must honor the SAME public contract.
"""

import json
import os

from spool import config as _config


class FileSpoolReader:
    def __init__(self, path):
        self.path = path

    def read_all(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def read_from(self, byte_offset):
        """Events starting at a BYTE offset into the spool file."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "rb") as fh:
            fh.seek(byte_offset)
            raw = fh.read().decode("utf-8")
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

    def offset_of_last(self):
        """Offset just past the end — callers store this as their next
        read_from position."""
        try:
            return os.path.getsize(self.path)
        except FileNotFoundError:
            return 0

    def truncate(self):
        """Reset the spool to empty (callers then continue at offset 0)."""
        with open(self.path, "w", encoding="utf-8"):
            pass


def open_reader(cfg=None):
    """Factory: backend selection by cfg['spool_backend']."""
    cfg = cfg or _config.get_config()
    if cfg["spool_backend"] == "file":
        return FileSpoolReader(cfg["spool_path"])
    raise ValueError(f"unknown spool backend: {cfg['spool_backend']}")
