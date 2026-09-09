"""Minimal CSV writing helper used by export paths."""

import csv
import os


def write_csv(path, header, rows):
    """Write header + rows (iterable of lists) to path, creating parent dirs."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return path
