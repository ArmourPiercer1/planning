# notification-retry (probe fixture)

A small notification service. Providers are called synchronously; on any
non-2xx the notification is marked `failed` and that is the end of it —
there is no retry today.

## Layout

- `app/provider.py` — `ProviderClient`: the delivery client. NOTE: its
  429 (rate-limit) response behavior is NOT documented; read the code and
  the tests to figure out what it actually returns.
- `app/notify.py` — `send_notification()`: builds a payload, calls the
  provider, stores the record.
- `app/db.py` — `NotificationStore`: JSON-file persistence.
- `app/api.py` — the HTTP surface (functions, framework-agnostic).
- `tests/test_notify.py` — the test suite that must stay green.

## Platform notes

- Python 3.11, stdlib only (tests use plain `unittest`).
- The provider client is the seam to the outside world; treat
  `ProviderClient.send()` as a frozen interface unless a spike proves
  otherwise.
