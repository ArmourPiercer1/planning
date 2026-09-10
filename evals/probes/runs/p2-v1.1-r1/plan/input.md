# Task: migrate the config store off JSON files

Ops wants the primary config store moved off `config.json`. The target
format is YAML. The hard part is not the parsing — it is that we do not
know what else reads `config.json` directly:

- `deploy/check.sh` definitely reads it at deploy time.
- There may be CI jobs, cron scripts, or sidecar tools that read it too.
  Nobody has a complete list.

A bounded probe (30–60 minutes: grep the repo + CI config + deploy
scripts for references to `config.json`, interview the deploy runbook)
will produce the answer: the complete set of external readers.

Depending on what the probe finds, the implementation forks into two
routes:

- **Route A (external readers exist beyond what we control):** keep a
  JSON *export* — primary store becomes YAML, `config.json` is
  regenerated on save so existing readers keep working.
- **Route B (only readers we own, and we can update them):** full cutover
  to YAML; update the readers we own; delete `config.json`.

Do not design both routes in detail now. Plan the probe and the minimal
shared preparation; the route-specific work belongs to the stage after
the probe reports.

Hard requirements:

- Startup validation behavior is unchanged.
- `set`/`show` CLI commands keep working with the same flags.
- Existing tests stay green.
