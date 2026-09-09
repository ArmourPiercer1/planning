# Orchestration — running the LLM phase

The runner is two-phase. **Phase 0 (prepare) and phases 2–3 (score/report) are
deterministic Python.** The LLM planning/execution phase runs **inside the
host session** as subagents, because the candidate variants must use the
planning skills exactly as a real planner would (hot-loaded from
`.agents/skills/`), and the host provides the subagent isolation needed to
avoid contamination.

## Invariants (anti-contamination)

1. A planning subagent sees **only** its `prompt.md`, `work/repo` (the copied
   fixture), `task.md`, the skills under the configured `skills_dir`, the
   glossary, and `plan-check.py`.
2. `case.json`, the case `README.md` (trap documentation), expected
   constraints, other cases, and any `reports/` output are **never** in a
   subagent's input set. Subagents are told to treat directories named
   `fixtures`/`expected`/`reports` as off-limits.
3. All variants run on the **same host model** (the host does not expose
   per-subagent model config in V1 — recorded in `spec.json.model`).
4. The **audit** subagent is a fresh subagent that receives only the plan
   directory + `plan-auditor` skill + glossary. It never sees the planner's
   prompt, the repo, or the case.
5. The **executor** subagent (execution smoke only) receives only its prompt,
   the work repo (with baseline commit), and the plan artifacts it needs one
   package at a time.

## Per-run procedure (one spec from `manifest.json`)

| Step | Who | Action |
|---|---|---|
| 1 | host | spawn a subagent with `<run_dir>/prompt.md` as its whole task (variant-specific) |
| 2 | subagent | explores `work/repo`, produces plan (structured artifacts or `plan.md`) into `out/`, self-reports every file read to `<run_dir>/telemetry.jsonl` |
| 3 | host | render host prompts: `render_host_prompts.py --run-id R [--exec CASE/VARIANT]`. Then (candidate + ablations **except** `ablation-full-minus-auditor`) spawn a **fresh** subagent with `audit-prompt-1.md`. If verdict FAIL **and the run is a candidate** → spawn a **revision** subagent with `revision-prompt.md` (fix in place, re-lint) → fresh auditor with `audit-prompt-2.md` (round ≤ 2 total; `audit.json.revision_round` records it). **Ablation runs get exactly one audit round and no revision**: the structural degradation from the removed stage is the expected signal, and letting the reviser re-add the ablated stage would contaminate the measurement. |
| 4 | host | write `<run_dir>/timing.json` with `{"wall_time_seconds": <planning+audit wall clock>}` — see "Wall time" below |
| 5 | host | `eval_runner.py score --run-id R` |

Execution smoke (optional, per-run flag): after scoring, spawn a fresh
executor subagent with `exec-prompt.md`, then
`eval_runner.py finalize-execution --run-dir <run_dir>` (which re-runs the
fixture test suite, parses git + telemetry, and fills the `execution` block
and the E vector). `finalize-execution` also adds the execution wall time
(first task start → last task end, from `execution-report.json.per_task`) to
`e_vector.wall_time`, so for an executed run the E vector carries the full
planning + execution span.

## Why a workflow template

For a full run (all cases × variants) the host drives steps 1–4 with the
`workflow` tool using `runners/workflow_template.js` as the skeleton: one
agent per spec, a barrier per case, audit/revision loops in-script, wall
times captured by the script, `timing.json` written by the script before the
planner's context is dropped. The template is a **documented skeleton with
placeholders**, not a committed executable artifact — the host renders and
runs it per invocation so the exact subagent count can be tuned.

## Wall time

`e_vector.wall_time` comes from `<run_dir>/timing.json`
(`wall_time_seconds`), which the **host** writes after the LLM phase. Two
proven ways to measure it:

- **workflow-driven** (recommended): wrap each `agent()` call in the workflow
  script with `Date.now()` (the workflow runtime exposes `Date`; the
  no-timers restriction covers `setInterval`/`setTimeout`, not `Date`). Sum
  planning + audit (+ revision) wall clocks per run; the smoke run
  (`runs/smoke-v1`) used exactly this.
- **manual subagent-driven**: have the host time the wall clock around each
  spawn (e.g. record before/after timestamps in the session) and write the
  sum.

Be explicit in `timing.json.note` about what the number covers — it is the
planning loop (audit rounds included), not the executor's time.

## Host operations notes (DSH sandbox)

- **Deleting run dirs**: `prepare` refuses to overwrite an existing run id.
  To redo a run, delete the dir first with **pwsh `Remove-Item -Recurse
  -Force`** — Python `os.unlink`/`shutil.rmtree` can be denied on some files
  (observed on `.git/objects/*`) even though the same delete succeeds via
  pwsh. If pwsh is also denied (directories created with an explicit `0o700`
  mode — avoid `tempfile.mkdtemp` in fixture/executor code for the same
  reason), one-shot escalate with `danger-full-access`.
- **Prompt templates use `{placeholder}`** rendered by plain `str.replace`
  (never `str.format`), so literal JSON braces in examples stay single-brace.

## Telemetry protocol (all subagents)

Append-only JSON lines to `<run_dir>/telemetry.jsonl`:
`{"ts":"<iso8601>","op":"read|write","path":"<absolute path>"}`.
`read` = any file opened for content (including skills and the gate script —
filter by path at scoring time if needed). Self-reporting is the V1 honesty
mechanism: the scorer counts unique repo paths as `context_read` and flags
implausibly low counts as context starvation (G3).

## Tokens / compactions

The host does not expose per-subagent token usage or compaction events in
V1. `e_vector.tokens` and `e_vector.compactions` stay `null` with a note;
the schema fields are reserved so a later host release can fill them without
changing the runner.
