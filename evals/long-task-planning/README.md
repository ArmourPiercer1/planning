# Long-Task-Planning Evals

Evaluation infrastructure for the **Planning Compiler** skills
(`.agents/skills/long-task-planning/` + 9 stage skills). It measures *plan
quality* — not unique-DAG identity — with deterministic scoring first and
explicit **judge-pending** entries where a dimension is not programmatically
decidable (bootstrap `long_task_planning_evals_bootstrap.md` §1–§16).

This directory is a **two-phase runner**:

- **Phase 0 + phases 2–3 are deterministic Python** (`runners/eval_runner.py`):
  `prepare` → `score` → `finalize-execution` → `report`.
- **Phase 1 (planning / audit / execution) runs as fresh subagents in the host
  session** (a `workflow` script or manual subagent spawns), because the
  candidate must use the skills exactly as a real planner would, and the host
  provides the isolation needed to prevent contamination.

See `runners/ORCHESTRATION.md` for the invariants and the step table.

## Directory layout

```
evals/long-task-planning/
├── README.md                     ← you are here
├── schemas/
│   ├── case.schema.json          machine-readable per-case constraints
│   ├── run-spec.schema.json      per-run identity (case, variant, model, paths)
│   └── run-result.schema.json    per-run scored result incl. the E vector
├── fixtures/                     14 independent cases (A–L + 2 hybrids)
│   └── case-NN-name/
│       ├── repo/                 stdlib + unittest fixture (green by default;
│       │   └── tests/__init__.py required — see "Adding a case")
│       ├── task.md               the task prompt (all the subagent gets)
│       ├── case.json             anchors + expected constraints (never shown)
│       └── README.md             trap documentation (never shown to subagents)
├── runners/
│   ├── eval_runner.py            prepare / score / finalize-execution / report
│   ├── render_host_prompts.py    renders audit / revision / executor prompts
│   ├── ORCHESTRATION.md          anti-contamination invariants + step table
│   ├── workflow_template.js      documented skeleton for the workflow tool
│   └── prompts/                  candidate / baseline-a / baseline-b /
│                                 audit / revision / executor templates
├── scorers/
│   ├── static_scorer.py          L1 static plan-quality scoring (both variants)
│   ├── prose_parser.py           free-form/checklist baseline parser
│   └── aggregate.py              per-variant aggregation + report rendering
├── runs/                         prepared runs (work/ repos git-ignored)
│   └── smoke-v1/                 the committed smoke run (evidence)
└── reports/                      rendered reports (smoke-v1-report.{md,json})
tests/planning-evals/             test_evals.py + run_tests.py + run_all.ps1
```

## The four layers (bootstrap §5)

| Layer | What | Status here |
|---|---|---|
| L1 static plan quality | constraint satisfaction on the plan artifact | **P0, implemented** (`static_scorer.py`) |
| L2 challenge benchmark | traps A–L encoded as `case.json` constraints | **P0, 14 cases** |
| L3 execution fidelity | does the plan survive one execution pass | **P1, smoke implemented** (`finalize-execution`) |
| L4 robustness | perturbation / adversarial inputs | P2 — next (see "Next") |

## Cases (14)

Machine-readable constraints live in each `case.json`; traps in each case
`README.md`. `mh`=must-have edges, `mnh`=forbidden edges, `par`=parallelizable
group, `fpp`=forbidden-parallel pair (shared-path hazard), `notown`=must-not-own
path, `replan`=required replan actions, `ccp`=required contract-change path,
`rec`=recoverable anchors.

| Case | Type | Title | Probes |
|---|---|---|---|
| case-01-weekly-batch-export | A | Weekly batch export: wiring existing parts, not a new feature | mh,mnh,par,rec |
| case-02-durable-sms | B | Durable SMS: one module, three different contexts | mh,mnh,par,rec |
| case-03-discount-loyalty | C | Bulk + loyalty discounts: two features, one shared registry | mh,fpp |
| case-04-audit-async | D | Async audit logging: producer/consumer coupled only by the event contract | mh,mnh,par,rec |
| case-05-statement-view | E | Statement view: hidden shape seam at the ledger API boundary | mh |
| case-06-payslip-summary | F | Payslip summary: legacy export sits one file over | mh,notown |
| case-07-reliable-delivery | G | Retry + dead-letter: the deliver() contract cannot carry a reason | mh,ccp |
| case-08-avatar-field | H | avatar_url across five layers: the mega-task temptation | mh,par |
| case-09-rounding-fix | I | Rounding fix: two domains, one tiny shared context | — |
| case-10-timeout-seam | J | Integration-only bug: unit-green, e2e-red timeout key mismatch | mh,ccp (designed-fail repo) |
| case-11-billing-branches | K | Late fees + refunded section: two branches that must not couple | mh,mnh,par,rec |
| case-12-spool-backends | L | Memory spool backend: a contract that is partly infeasible | mh,replan,rec |
| case-13-crm-exports | hybrid C+E | V2 export: shared request layer + byte-frozen v1 seam | mh,par,fpp,rec |
| case-14-iot-push-receipt | hybrid F+G | Push receipts: contract change + legacy bait | mh,notown,ccp,rec |

case-10 ships a **designed-failing** test
(`test_pipeline_e2e_effective_timeout`); `validate-fixtures` asserts the
failing set equals `repo_tests_expected_failures` exactly, so the smoke can
prove the executor fixed the real bug.

## Scoring rules (L1)

`static_scorer.score_candidate_plan(case, plan_dir)` reuses the Task-1
`plan-check.py` gate (`Plan.load()/run()`) plus constraint checks. The nine
report metrics and where they come from:

| Metric | Source | Coverage |
|---|---|---|
| Contract completeness | 9 required `stage-contract.json` fields present & non-trivial | assessed |
| Acceptance determinism | acceptance text: no vague words + evidence marker | assessed |
| Context locality (amplification proxy) | `context_files / owned_files` per leaf | assessed |
| Hazardous ownership collisions | both tasks **own** a shared path (fpp) / anchor cap | assessed |
| Dependency precision (must-have hit rate) | directed edge or internalization per `must_have_edges` | assessed |
| Integration explicitness (case reqs met) | gate kind + anchors + `failure_path_markers` keywords | assessed |
| Phase-shaped leaves | leaves with > `max_anchors_per_task` anchors | assessed |
| Local recoverability | `checkpoint_required` on `recoverable_tasks` | assessed (structural) |
| Scope discipline | `must_not_expand_scope`/`must_not_own` mentioned/owned | assessed |

Programmatic-first rule: dimensions that cannot be decided without judgment
(e.g. prose recoverability, contract-change *quality*) are emitted as
`judge_pending` entries with a reason — **never a guessed number**.

Baselines (`score_prose_plan`) get keyword/structural proxies (coverage
`partial`); dimensions with no signal in prose are `n/m` — **an `n/m` cell is
not a zero** (see the report legend).

### Anti-gaming guards (§13)

| Flag | Fires when | Why it is a game |
|---|---|---|
| G1_OVER_FRAGMENTED | leaf count > range max | many tiny tasks read as "fine-grained" |
| G2_ALL_SERIAL | par group present but no edges at all, or every par group ordered | "serial" is not a plan; for structured plans a par group ordered **only via a downstream integration task** does *not* fire (integration tasks are excluded from group membership by design) |
| G3_CONTEXT_STARVATION | >30% of structured leaves declare no context / >50% of prose task lines name no file | omitting context looks like "locality" |
| G5_MEGA_INTEGRATION | one integration task owns fixes for >50% of leaves | one blob "integration" task |
| G6_BLOCKER_ESCAPE | >50% of failure cases are blocker-laden | deferring everything to blockers |

Gaming flags are **data, not failure**: they annotate the metric so a reader
can see *how* a score was produced.

## The E vector (bootstrap §2.4)

Every run emits the raw 10-dimension vector
`(success, wall_time, tokens, context_read, rework, integration_defects,
scope_creep, replans, compactions, local_recoverability)` — raw dimensions are
never dropped. Planning-phase runs fill what is measurable
(`success`, `scope_creep`, `replans`, `context_read` via the locality proxy,
`local_recoverability`, `wall_time`) and leave the rest `null` with a note.
`finalize-execution` overwrites `success`, `context_read`, `rework`,
`integration_defects`, `replans`, `local_recoverability` and **adds** the
execution wall time to `wall_time`.

- `tokens` / `compactions`: **not observable from the host per subagent in
  V1** → `null` + note (schema fields reserved).
- `context_read`: unique self-reported telemetry reads.
- `rework`: churn-based `(added+deleted−net_added)/churn` across the
  executor's commits; definition recorded in the result.
- `wall_time`: host-measured (workflow `Date.now()` or manual), written to
  `timing.json`; planning+audit for planning runs, + execution for executed
  runs. See `runners/ORCHESTRATION.md` → "Wall time".

## How to run

All commands from the repo root, with the workspace-local uv cache:

```powershell
$env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"
python = "uv run --no-project python"

# 0. sanity: schemas + anchors + fixture repo tests (case-10: designed fails)
& $python evals/long-task-planning/runners/eval_runner.py validate-fixtures

# 1. prepare: copy repos, git baseline commit, render prompt.md, write spec.json
& $python evals/long-task-planning/runners/eval_runner.py prepare `
    --run-id my-run --cases case-04-audit-async,case-10-timeout-seam `
    --variants candidate,baseline-a,baseline-b `
    --ablations full-minus-integration --ablation-cases case-10-timeout-seam

# 2. render host-side prompts (audit/revision/executor) after the plans exist
& $python evals/long-task-planning/runners/render_host_prompts.py `
    --run-id my-run --exec case-10-timeout-seam/candidate

# 3. the LLM phase — host subagents (workflow tool or manual):
#    - one planner per run dir, prompt = <run_dir>/prompt.md
#    - candidate/ablation: fresh auditor (audit-prompt-1.md); FAIL +
#      candidate → revision (revision-prompt.md) → auditor round 2 (max 2)
#    - ablation: exactly ONE audit round, no revision
#    - executor (if --exec): exec-prompt.md, one package at a time
#    - measure wall time per run (Date.now() in the workflow script)

# 4. host writes <run_dir>/timing.json per run:
#    {"wall_time_seconds": <planning+audit wall>, "note": "..."}

# 5. score + (if executed) finalize + report
& $python evals/long-task-planning/runners/eval_runner.py score --run-id my-run
& $python evals/long-task-planning/runners/eval_runner.py finalize-execution `
    --run-dir evals/long-task-planning/runs/my-run/case-10-timeout-seam/candidate
& $python evals/long-task-planning/runners/eval_runner.py report --run-id my-run
```

- `prepare` **refuses to overwrite** an existing run id; delete the dir first
  (pwsh `Remove-Item -Recurse -Force` — see "Sandbox notes").
- `--ablations` picks stage-removal variants (`full-minus-integration`,
  `full-minus-risk`, `full-minus-decomposer`, `full-minus-auditor`);
  `--ablation-cases` restricts them to listed cases. Ablations degrade
  **honestly** (missing artifact = expected finding, not an error).
- `full-minus-auditor` skips the auditor entirely (no `audit.json`).
- **Version comparison**: run the same cases twice with different
  `--skills-dir` (e.g. a skill branch copy) under two run ids; the report
  renders per-variant side-by-side. `spec.json.model` records the
  identity/note.

### How to read results

- **Read the E vector first**; the metric tables are conveniences.
- **Never read a single metric** (each has a documented gaming mode — see
  the report's "How to read this report" section and the guard table above).
- Per-variant: means/min/max + **Measured n/m** (how many runs actually
  produced the dimension) + worst run. `n/m` = not measurable from the
  artifact form, **not** zero.
- Per-case matrix: `lint`/`LINT-FAIL`, `mnh✓`/`mnh✗ v/t`, `CREEP×n`,
  `count✓/✗` — a compact constraint-satisfaction view.
- Judge-pending entries are listed per variant with reasons; they are the
  work queue for the LLM judge (out of scope in V1).

### Sandbox notes (DSH workspace-write)

- **No `tempfile.mkdtemp`/`TemporaryDirectory`** in fixture or executor code:
  the sandbox denies file writes/scandir/delete under directories created
  with an explicit `0o700` mode — exactly what `mkdtemp` passes. Use plain
  `os.mkdir` scratch dirs (see `tests/` and `executor.md` hard rules).
- Python `os.unlink`/`shutil.rmtree` can be denied on some files (observed
  on `.git/objects/*`) where pwsh `Remove-Item` succeeds; the test suite
  falls back to pwsh. 0o700 dirs need a one-shot `danger-full-access`.

## The smoke run (committed evidence)

`runs/smoke-v1/` + `reports/smoke-v1-report.md` — 3 cases ×
{candidate, baseline-a, baseline-b} + `full-minus-integration` ablation on
case-10 + an execution smoke of the case-10 candidate plan. Highlights:

- **Candidates**: lint 0, audit PASS (2 of 3 needed a revision round),
  dependency precision 1.0, contract completeness 1.0, no ownership
  collisions, scope discipline 1.0, no gaming flags.
- **Baselines**: contract completeness ~0.67, dependency precision
  0.17–0.28, integration explicitness 0.17–0.33; G1/G3 flags on all
  (prose over-fragments and starves context); case-04 baseline-b created the
  forbidden producer→consumer edge (`mnh✗ 1/1`) — exactly the Type-D trap.
- **Ablation (−integration)**: LINT-FAIL, audit FAIL (2 blockers), success
  false — the expected, honest degradation signal.
- **Execution smoke**: the case-10 candidate plan executed to
  `success=true`, 15/15 tests green (including the designed-failing
  `test_pipeline_e2e_effective_timeout`), 4 checkpoints, 0 integration
  defects, rework ratio 0.0154.

## Tests

```powershell
pwsh tests/planning-evals/run_all.ps1
```

30 tests: fixture invariants (≥12 cases, schema, anchors, type coverage A–L +
hybrid, **scope-bait must not conflict with anchors**), candidate scoring on
`examples/long-task-planning/` (synthetic case-99), prose scoring, a full
prepare→score→report round trip (selftest run, cleaned after), schema
conformance, aggregation, prompt/orchestration hygiene.

## Next (L3/L4)

- Execution fidelity at scale: run all candidate plans, compare
  `rework`/`integration_defects`/`success` across cases and skill versions.
- L4 robustness: perturbed task prompts (ambiguous scope, missing files),
  adversarial repos (near-miss files), repeated runs for variance (seeds).
- LLM judge for the `judge_pending` dimensions with a fixed rubric, kept
  separate from programmatic scores.
