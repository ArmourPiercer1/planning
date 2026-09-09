# Task: weekly batch export

The analytics service currently computes metrics on demand and writes CSV on
demand. Product wants a scheduled export:

- Every **Monday at 06:00** (server time), produce
  `exports/weekly/weekly-<ISO date of that Monday>.csv` (e.g.
  `exports/weekly/weekly-2026-07-06.csv`).
- The file covers the **last 7 days** (the Monday itself back to the
  previous Monday, inclusive) and contains one row per day:
  `date, revenue, active_users`.
- Use the **existing scheduler** (`analytics/scheduler.py`) and the
  **existing CSV writer** (`analytics/csv_writer.py`).

Requirements:

- All existing tests must keep passing.
- Add tests for the new export path. The export function must be callable
  directly (not only through the scheduler) so it can be unit-tested.
- Do not change the public signatures of the existing helpers.

The repo layout:

```
analytics/
  __init__.py
  metrics.py       # daily_revenue(rows), active_users(rows)
  queries.py       # filter_range(rows, start, end), last_n_days(today, n)
  csv_writer.py    # write_csv(path, header, rows)
  scheduler.py     # register(name, schedule, fn), run_jobs_for(date, time)
tests/
  test_analytics.py
```
