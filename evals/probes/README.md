# v1.1 Probe Validation (Stage C2)

Purpose: prove the **contract-closed v1.1 candidate** behaves correctly on
six targeted failure modes — using ONE candidate run per probe,
deterministic scoring, no big benchmarks, no repeated sampling, no LLM
judges.

## Probe set

| Probe | Question | Fixture | Pass bar |
|---|---|---|---|
| P1 | Meta-planning runaway | `repos/p1-notification-retry` | PASS: governor stops at SPIKE, optimization/storm deferred, budget within limits (1 audit ideal) |
| P2 | Horizon boundary | `repos/p2-config-migration` | PASS: detailed = probe + ≤1 prep task; forecast carries both routes with no leaf task ids; stop_after = probe |
| P3 | No over-split | `repos/p3-log-rotation` | PASS: ≤4 tasks, no spike, single stage |
| P4 | True blocker retention | `repos/p4-audit-log` | PASS: EXECUTION_BLOCKER with acceptance_ref → governor HUMAN_BLOCKER; no fake second-store solution |
| P5 | Legacy planning quality | `repos/p5-report-export` | PASS: plan-check clean; dependencies/parallel/ownership/integration/scope quality no worse than v1.0 baseline |
| P6 | Cross-stage drift | `repos/p6-cross-drift` (stage-1 baseline frozen in `stage-1/`) | PASS: frozen C1 change is surfaced (not silently EXECUTE'd); notification failure policy + webhook reuse present |

Verdicts (per probe): `PASS` / `PASS_WITH_NOTES` / `PATCH_REQUIRED` /
`REOPEN_ARCHITECTURE`. Baseline runs (v1.0, P1 and P5 only) are recorded,
not judged.

## Execution model

- Each v1.1 probe = one orchestrator run of the `long-task-planning`
  pipeline (stages 0–8) against the fixture repo, writing all artifacts to
  `runs/<probe>-v1.1-<runid>/plan/`.
- P1 and P4 additionally run the audit stage (7) in a **fresh, isolated
  auditor subagent** (the behavior under test depends on auditor
  independence); P2/P3/P5/P6 audit in-conversation and record that fact in
  the run manifest.
- Baselines (P1, P5) use the v1.0 skills checked out to
  `baseline-v1.0/skills/` (commit 59b78e3) — no governor stage in v1.0;
  the recorded numbers (audit count, subagents, task count) are the
  comparison point.
- Scoring: `run_probe.py --probe <id> --version <v> --run <runid>
  --plan-dir <dir>` → writes `results/<probe>-<version>-<runid>.json`
  (schema `planning/probe-run-result@1`). Scoring is deterministic:
  plan-check lint + structural checks on the produced artifacts only.

## Rules (from the closing plan)

- C2 uses **only the C1 candidate** — no skill edits during probes.
- A probe that fails gets a **targeted patch** (C1 package scope only),
  then re-run of the failed probe + core smoke (P3/P5 class), never a
  redesign.
- After C2 the baseline is frozen as *Planning Skills v1.1 —
  Contract-Closed Probe-Validated Baseline*; no v1.2, no runtime work.
