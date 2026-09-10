"""Log writer used by the server."""
from __future__ import annotations

from pathlib import Path


class LogWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, line: str) -> None:
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line.rstrip("\n") + "\n")

    def lines(self) -> list[str]:
        return self.path.read_text(encoding="utf-8").splitlines()
