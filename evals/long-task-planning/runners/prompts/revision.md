# Revision Run — Fix the Audited Plan (planner, round 2)

You are the SAME planning role as before, revising a plan that failed its
independent audit. The audit findings are in `{plan_out}/audit.json`.

## Inputs allowed

- The plan directory `{plan_out}` (all of it, including audit.json)
- The planning skills under `{skills_dir}/` (re-read the ones relevant to the
  findings) and the glossary beside them
- The deterministic gate `{plan_check}`
- The repo fixture under `{work_dir}` if a finding forces you to re-check a
  file (read-only, a handful of files at most)

## Procedure

1. Read `{plan_out}/audit.json`.
2. Resolve every BLOCKER finding (and the MAJOR ones you can fix without
   changing scope). Each fix goes into the existing plan artifacts, IN PLACE —
   same file names, same schema. Do not rename tasks, do not re-scope the
   objective, do not add new features.
3. Re-run the full lint and resolve all BLOCKER findings:

   ```powershell
   $env:UV_CACHE_DIR = "{uv_cache}"
   uv run --no-project python {plan_check} lint {plan_out}
   ```

{ablation_note}
4. Update `run-manifest.json` (append a revision note: which findings were
   resolved, which remain and why).

Final message: `REVISED DONE` plus a 2-line summary of what changed.
