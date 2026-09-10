"""Tiny request server loop (fixture: one tick = one request)."""
from __future__ import annotations

import time

from .logger import LogWriter


def serve(writer: LogWriter, requests: list[str]) -> None:
    for req in requests:
        handle(req)
        writer.append(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {req}")


def handle(req: str) -> str:
    if not req:
        return "400"
    return "200"


if __name__ == "__main__":
    serve(LogWriter("logs/app.log"), ["GET /", "GET /health"])
