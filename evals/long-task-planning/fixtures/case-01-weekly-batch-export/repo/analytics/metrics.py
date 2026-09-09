"""Metric computations for the analytics service.

Inputs are flat row lists (the service reads from a warehouse dump); no I/O
happens here.
"""


def daily_revenue(rows):
    """Sum revenue per day.

    rows: [{'date': 'YYYY-MM-DD', 'amount': float}, ...]
    Returns {'YYYY-MM-DD': float}.
    """
    by_day = {}
    for r in rows:
        by_day[r["date"]] = by_day.get(r["date"], 0.0) + r["amount"]
    return by_day


def active_users(rows):
    """Count distinct users per day.

    rows: [{'date': 'YYYY-MM-DD', 'user_id': str}, ...]
    Returns {'YYYY-MM-DD': int}.
    """
    by_day = {}
    for r in rows:
        by_day.setdefault(r["date"], set()).add(r["user_id"])
    return {d: len(s) for d, s in by_day.items()}


WEEKLY_METRICS = ("daily_revenue", "active_users")
