"""Query construction helpers (date-range filtering over row lists)."""

import datetime as _dt


def filter_range(rows, start, end):
    """Inclusive date-range filter on rows with a 'date' key (YYYY-MM-DD)."""
    return [r for r in rows if start <= r["date"] <= end]


def last_n_days(today, n):
    """Return (start, end) ISO dates covering the last n days ending at today."""
    end = _dt.date.fromisoformat(today)
    start = end - _dt.timedelta(days=n - 1)
    return start.isoformat(), end.isoformat()
