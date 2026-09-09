"""Spool configuration and backend selection."""

import copy

DEFAULT_CONFIG = {
    "spool_backend": "file",   # "file" (default) | "memory" (not implemented yet)
    "spool_path": "spool.jsonl",
}

CONFIG = copy.deepcopy(DEFAULT_CONFIG)


def get_config():
    return copy.deepcopy(CONFIG)


def set_config(cfg):
    global CONFIG
    CONFIG = copy.deepcopy(cfg)


def reset_config():
    set_config(DEFAULT_CONFIG)
