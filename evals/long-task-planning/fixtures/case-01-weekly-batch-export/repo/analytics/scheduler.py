"""Tiny cron-style scheduler.

Jobs are registered as (name, schedule, callable) where schedule is a string
of the form '<weekday> <HH:MM>', e.g. 'mon 06:00'.
"""

import datetime as _dt

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_JOBS = []


def register(name, schedule, fn):
    """Register a job; duplicate names are rejected."""
    if any(j[0] == name for j in _JOBS):
        raise ValueError(f"job already registered: {name}")
    _JOBS.append((name, schedule, fn))


def jobs():
    """Return the registered jobs as a list of (name, schedule, fn)."""
    return list(_JOBS)


def run_jobs_for(date_str, time_str):
    """Run every job whose schedule matches the given date and time.

    Returns the list of job names that fired.
    """
    wd = _WEEKDAYS[_dt.date.fromisoformat(date_str).weekday()]
    fired = []
    for name, schedule, fn in _JOBS:
        day, tm = schedule.split()
        if day == wd and tm == time_str:
            fn()
            fired.append(name)
    return fired
