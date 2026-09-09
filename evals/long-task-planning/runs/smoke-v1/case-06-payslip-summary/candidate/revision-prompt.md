# Revision Run — Fix the Audited Plan (planner, round 2)

You are the SAME planning role as before, revising a plan that failed its
independent audit. The audit findings are in `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\out/audit.json`.

## Inputs allowed

- The plan directory `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\out` (all of it, including audit.json)
- The planning skills under `D:\AI_Coworking\skill-build\planning\.agents\skills/` (re-read the ones relevant to the
  findings) and the glossary beside them
- The deterministic gate `D:\AI_Coworking\skill-build\planning\.agents\scripts\plan-check.py`
- The repo fixture under `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\work\repo` if a finding forces you to re-check a
  file (read-only, a handful of files at most)

## Procedure

1. Read `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\out/audit.json`.
2. Resolve every BLOCKER finding (and the MAJOR ones you can fix without
   changing scope). Each fix goes into the existing plan artifacts, IN PLACE —
   same file names, same schema. Do not rename tasks, do not re-scope the
   objective, do not add new features.
3. Re-run the full lint and resolve all BLOCKER findings:

   ```powershell
   $env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"
   uv run --no-project python D:\AI_Coworking\skill-build\planning\.agents\scripts\plan-check.py lint D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-06-payslip-summary\candidate\out
   ```


4. Update `run-manifest.json` (append a revision note: which findings were
   resolved, which remain and why).

Final message: `REVISED DONE` plus a 2-line summary of what changed.
