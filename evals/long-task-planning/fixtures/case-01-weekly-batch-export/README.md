# case-01 — trap documentation (NEVER shown to planning subagents)

**Type A — fake feature boundary.** The task prompt frames this as "a new
weekly export feature". In the repo, every building block already exists:
metrics, queries, scheduler, CSV writer. The whole job is a small wiring
change plus tests.

What good plans look like:
- 2–5 tasks (range in case.json); the compute closure (metrics + queries)
  is ONE task — the 7-day pipeline needs both files in a single context.
- Scheduler registration and CSV layout are separate small tasks, parallel
  once the compute closure exists.
- The export entry function + schedule string + path pattern are frozen as
  a seam contract; an e2e gate fires the job (or calls the function directly)
  and checks the file.

What traps look like:
- One mega-task "implement weekly batch export" (oversized leaf, 4 anchors).
- 8+ micro-tasks ("create exports dir", "add import statement", ...) —
  over-fragmentation.
- Serial chains A2→A1→A4→A3→A2-style fake dependencies, e.g. "scheduler
  after queries" (no such direct dependency).
- Invented scope: alerts on failure, dashboard, backfill of past weeks —
  none of these are asked for; case.json lists `analytics/alerts.py` and
  `analytics/dashboard.py` as must-not-expand paths.

Scoring notes:
- `context_clusters` encodes merge([A1,A2]) / separate([A3,A4]).
- The e2e gate markers require the failure scenarios (job not fired, empty/
  malformed file) to be present in the integration plan's gate text.
