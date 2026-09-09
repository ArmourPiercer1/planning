"""Render host-side prompts (audit / revision / execution) for a prepared run.

`prepare` renders the PLANNING prompts (prompt.md) that the subagent reads.
The audit, revision and execution prompts are rendered host-side, after the
planning agents finish, because their round/variant wiring is an
orchestration concern (see ORCHESTRATION.md):

    uv run --no-project python evals/long-task-planning/runners/render_host_prompts.py \
        --run-id smoke-v1 --exec case-10-timeout-seam/candidate

Per run dir this writes:
  - audit-prompt-1.md          (auditor, round 1) — every audited run
  - audit-prompt-2.md          (auditor, round 2) — candidate runs only
  - revision-prompt.md         (planner fix pass) — candidate runs only
  - exec-prompt.md             (executor)         — runs listed in --exec

Ablation runs are audited once (single round, no revision): the structural
degradation from the removed stage is the expected signal, and letting the
reviser re-add the ablated stage would contaminate the measurement.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent
RUNS = EVALS / "runs"
PROMPTS = HERE / "prompts"
ROOT = EVALS.parents[1]
SKILLS = ROOT / ".agents" / "skills"
GLOSSARY = ROOT / ".agents" / "references" / "glossary.md"
SNAPSHOT_SCRIPT = ROOT / ".agents" / "scripts" / "repo-snapshot.py"
PLAN_CHECK = ROOT / ".agents" / "scripts" / "plan-check.py"
UV_CACHE = ROOT / ".cache" / "uv"


def render(tpl: Path, run_dir: Path, out_name: str, **extra) -> Path:
    text = tpl.read_text(encoding="utf-8")
    subs = {
        "task_prompt": str(run_dir / "task.md"),
        "work_dir": str(run_dir / "work" / "repo"),
        "plan_out": str(run_dir / "out"),
        "telemetry_file": str(run_dir / "telemetry.jsonl"),
        "skills_dir": str(SKILLS),
        "glossary": str(GLOSSARY),
        "plan_check": str(PLAN_CHECK),
        "snapshot_script": str(SNAPSHOT_SCRIPT),
        "repo_fixture": str(run_dir / "work" / "repo"),
        "uv_cache": str(UV_CACHE),
        "scopes": "",
        "ablation_block": "",
    }
    subs.update(extra)
    for k, v in subs.items():
        text = text.replace("{%s}" % k, str(v))
    out = run_dir / out_name
    out.write_text(text, encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--exec", action="append", default=[], metavar="CASE/VARIANT",
                    help="run(s) that get an exec-prompt.md (repeatable)")
    ap.add_argument("--skip-audit", action="append", default=[], metavar="CASE/VARIANT",
                    help="audited run(s) that should NOT get audit/revision prompts")
    args = ap.parse_args()

    run_root = RUNS / args.run_id
    manifest_p = run_root / "manifest.json"
    if not manifest_p.exists():
        print(f"no manifest at {manifest_p} — run prepare first")
        return 2
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    skip = set(args.skip_audit)

    written = 0
    for s in manifest["specs"]:
        run_dir = Path(s["run_dir"])
        variant = s["variant"]
        key = f"{s['case_id']}/{variant}"
        audited = (variant in ("candidate",) or variant.startswith("ablation-")) and key not in skip
        if audited:
            written += 1
            print(f"[render] {key}: audit-prompt-1.md")
            render(PROMPTS / "audit.md", run_dir, "audit-prompt-1.md", round="1")
            if variant == "candidate":
                print(f"[render] {key}: audit-prompt-2.md, revision-prompt.md")
                render(PROMPTS / "audit.md", run_dir, "audit-prompt-2.md", round="2")
                render(PROMPTS / "revision.md", run_dir, "revision-prompt.md", ablation_note="")
        if key in args.exec:
            written += 1
            print(f"[render] {key}: exec-prompt.md")
            render(PROMPTS / "executor.md", run_dir, "exec-prompt.md")
    print(f"rendered {written} host prompt(s) under {run_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
