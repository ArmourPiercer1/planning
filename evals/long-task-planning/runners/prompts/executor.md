# Execution Run — Execute the Plan (execution smoke)

You are a fresh execution agent. Execute the plan in `{plan_out}` against the
repository in `{work_dir}` (a git repo with one baseline commit).

Follow the executor contract in
`{skills_dir}/long-task-planning/references/execution-protocol.md`.

## Protocol

1. Determine task order from `{plan_out}/dag.json` (integration tasks run
   after the leaves they verify). Then work strictly one package at a time:
   read **only** `{plan_out}/tasks/<task-id>.json` plus the files listed in
   its `required_context`. Do not read other plan artifacts.
2. Implement inside `{work_dir}`. If you must open a file not in the package,
   open at most one extra file, and record it as a `deviation` in the
   checkpoint. Never modify another task's owned paths.
3. Discovered problems: classify A (fix in place, inside owned paths) /
   B (record in the checkpoint backlog) / C (blocker — a frozen contract is
   wrong or a core seam is broken): write the checkpoint with
   `status: "blocked"` and STOP.
4. At each stable subgoal and at task completion:
   - `git -C {work_dir} add -A` and `git -C {work_dir} commit -q -m "<task-id>: <subgoal>"`
     (identity: use `-c user.name=eval-executor -c user.email=eval@local`);
   - write `{plan_out}/checkpoints/<task-id>.json` (schema
     `planning/checkpoint@1`) with concrete `verified_facts`.
5. Telemetry (mandatory): append one JSON line per file read to
   `{telemetry_file}`: `{"ts":"<iso>","op":"read","path":"<path>"}`.
6. Record per-task wall time (start/end epoch seconds) and, at the end, run
   the full repo test suite and record the result:

   ```powershell
   $env:UV_CACHE_DIR = "{uv_cache}"
   uv run --no-project python -m unittest discover -s {work_dir}/tests -t {work_dir}
   ```

   Write `{plan_out}/execution-report.json`:
   ```json
   {"per_task": [{"task_id":"T01","start":0.0,"end":0.0}],
     "tests": {"passed":0,"failed":0,"failures":[]},
     "integration_defects": 0,
     "notes": "..."}
   ```
   `integration_defects` = defects discovered only at integration/E2E time
   (leaf unit tests were green).

## Hard rules

- Never modify plan artifacts (only write checkpoints/ and execution-report.json).
- If you hit a C-class blocker, stop cleanly: the partial state must still be
  committed and checkpointed.
- Sandbox quirk: this environment's file sandbox denies access under
  directories created with an explicit `0o700` mode — exactly what
  `tempfile.mkdtemp` / `tempfile.TemporaryDirectory` pass. If a test needs a
  scratch directory, use plain `os.mkdir(path)` (no mode argument) and
  `shutil.rmtree` in cleanup; never `tempfile`.

Final message: `EXEC DONE` + tests passed/failed + any blockers.
