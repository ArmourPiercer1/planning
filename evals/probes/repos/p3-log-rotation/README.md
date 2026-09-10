# logservice (probe fixture)

A small long-running service that appends every request line to
`logs/app.log`. The file grows without bound; nothing rotates it.

## Layout

- `app/logger.py` — `LogWriter`: open/append helper used by the server.
- `app/server.py` — the service loop (request -> handle -> log line).
- `logs/app.log` — the live log (sample content included).
- `tests/test_log.py` — the suite that must stay green.

## Platform notes

- Python 3.11, stdlib only. The service may use `logging` or plain file
  handling; either is fine. No scheduler dependency is available — if a
  rotation schedule is needed, it must be driven from the service loop or
  at startup, not by cron.
