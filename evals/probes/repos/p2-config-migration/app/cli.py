"""Ops CLI: set / show."""
from __future__ import annotations

import argparse
import json

from .config_store import JsonConfigStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="configctl")
    parser.add_argument("--path", default="config.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    p_set = sub.add_parser("set")
    p_set.add_argument("key")
    p_set.add_argument("value")
    args = parser.parse_args(argv)

    store = JsonConfigStore(args.path)
    if args.cmd == "show":
        print(json.dumps(store.as_dict(), indent=2, sort_keys=True))
    elif args.cmd == "set":
        store.set(args.key, args.value)
        print(f"set {args.key} = {args.value}")
    return 0
