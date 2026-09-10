# config-store (probe fixture)

A small service whose configuration lives in `config.json`, read at startup
and written by the admin CLI.

## Layout

- `app/config_store.py` — `JsonConfigStore`: get/set/save over `config.json`.
- `app/loader.py` — startup validation of the config.
- `app/cli.py` — `set`/`show` commands (used by ops).
- `deploy/check.sh` — the deploy-time health check (reads the config file
  directly — see it).
- `tests/test_config.py` — the suite that must stay green.

## Platform notes

- Python 3.11, stdlib only.
- `config.json` is the single source of truth today. Whether anything
  *else* (CI, cron, another service) reads it directly is an open
  question — the deploy script definitely does.
