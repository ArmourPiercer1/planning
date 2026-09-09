"""Eval runner for the long-task-planning skills evals.

Two-phase design (the LLM phase runs outside this script, driven by the
host session's subagents — see ORCHESTRATION.md):

    python eval_runner.py list-cases
    python eval_runner.py validate-fixtures
    python eval_runner.py prepare   --run-id R --cases all --variants candidate,baseline-a,baseline-b [--ablations ...] [--skills-dir ...]
    # ---- host session runs the planning/execution agents per runs/R/manifest.json ----
    python eval_runner.py score      --run-id R
    python eval_runner.py finalize-execution --run-dir runs/R/<case>/<variant>
    python eval_runner.py report     --run-id R

Zero dependencies (stdlib only). Run under the same uv invocation as the
planning gate so fixtures can be exercised:
    $env:UV_CACHE_DIR = "<repo>/.cache/uv"
    uv run --no-project python evals/long-task-planning/runners/eval_runner.py <cmd>
"""

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent
ROOT = HERE.parents[2]
FIXTURES = EVALS / "fixtures"
RUNS = EVALS / "runs"
REPORTS = EVALS / "reports"
SCHEMAS = EVALS / "schemas"
PROMPTS = HERE / "prompts"
SKILLS_DEFAULT = ROOT / ".agents" / "skills"
UV_CACHE = ROOT / ".cache" / "uv"
PLAN_CHECK = ROOT / ".agents" / "scripts" / "plan-check.py"

sys.path.insert(0, str(HERE.parent / "scorers"))
import static_scorer  # noqa: E402
import aggregate  # noqa: E402

VARIANTS = ["candidate", "baseline-a", "baseline-b"]
ABLATIONS = ["full-minus-decomposer", "full-minus-auditor", "full-minus-integration", "full-minus-risk"]
ABLATION_TEMPLATE = {
    "full-minus-decomposer": """
## Stage override (ablation: context-decomposer removed)

Skip the context-closure decomposition method entirely. Group the work the
way you naturally would (per module / per feature is acceptable, a single big
task is allowed). You MUST still produce `candidate-tasks.json` with the same
schema fields so downstream gates and scoring keep working — but do not use
the closure-first split rules, do not assign disjoint owned paths by closure,
and do not estimate context footprints.
""",
    "full-minus-integration": """
## Stage override (ablation: integration-planner removed)

Skip the integration-planning stage: no seam census, no integration tasks, no
E2E gates, no owns_fixes_for. Plan only the implementation (leaf) tasks. Do
NOT write `integration-plan.json` at all — the missing artifact is the
expected ablation outcome; do not create a stub.
""",
    "full-minus-auditor": """
## Stage override (ablation: plan-auditor removed)

Run the pipeline exactly as usual through the risk stage. Note that no
independent audit will follow your run — finish after the full lint is clean
and list any remaining findings in run-manifest.json.
""",
    "full-minus-risk": """
## Stage override (ablation: plan-risk-estimator removed)

Skip the risk-estimation stage: do not write `risk-estimates.json` and leave
each Task Package's `risk` block at the minimal schema-valid default (footprint
"M", no warnings, null justification) without analysis.
""",
}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _write(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


def list_cases() -> int:
    ok = 0
    for d in sorted(FIXTURES.iterdir()):
        if not d.is_dir() or not (d / "case.json").exists():
            continue
        c = json.loads(_read(d / "case.json"))
        errs = static_scorer.validate_json_against(c, SCHEMAS / "case.schema.json")
        marks = " " + ", ".join(errs[:3]) if errs else ""
        print(f"{c['id']:38s} type={c['type']:6s} anchors={len(c['anchors'])}{marks}")
        ok += 1
    print(f"\n{ok} case(s) in {FIXTURES}")
    return 0


def _run_repo_tests(repo: Path) -> tuple[int, set[str], str, str]:
    """Run the fixture repo's unittest suite.

    Returns (exit_code, failing_test_names, summary, tail) where summary is
    'ok' | 'failed' | 'crash' (crash = no unittest summary line, e.g.
    discovery/import failure — must never be mistaken for green).
    """
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(repo / "tests"), "-t", str(repo)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=repo, timeout=120)
    out = r.stdout + r.stderr
    failing = set(re.findall(r"^(?:FAIL|ERROR): (test_\w+)", out, flags=re.MULTILINE))
    if re.search(r"^OK$", out, flags=re.MULTILINE):
        summary = "ok"
    elif re.search(r"^FAILED \(", out, flags=re.MULTILINE):
        summary = "failed"
    else:
        summary = "crash"
    return r.returncode, failing, summary, out[-1200:]


def validate_fixtures() -> int:
    failures = 0
    for d in sorted(FIXTURES.iterdir()):
        if not d.is_dir() or not (d / "case.json").exists():
            continue
        cid = d.name
        c = json.loads(_read(d / "case.json"))
        errs = static_scorer.validate_json_against(c, SCHEMAS / "case.schema.json")
        if errs:
            print(f"[FAIL] {cid}: case.json schema: {errs[:3]}")
            failures += 1
            continue
        problems = []
        task_file = d / c["task_prompt_file"]
        if not task_file.exists():
            problems.append(f"task prompt missing: {c['task_prompt_file']}")
        repo = d / c["repo_fixture"]
        if not repo.is_dir():
            problems.append(f"repo fixture missing: {c['repo_fixture']}")
        else:
            for a in c["anchors"]:
                for f in a["files"]:
                    if not (repo / f).exists() and not (repo / f).is_dir():
                        problems.append(f"anchor {a['id']} file missing: {f}")
            if not (repo / "tests").is_dir():
                problems.append("repo has no tests/ dir (fixtures must ship automated tests)")
            else:
                code, failing, summary, tail = _run_repo_tests(repo)
                if summary == "crash":
                    problems.append(f"test suite CRASHED (no unittest summary): {tail[-300:]}")
                expected_fail = set(c.get("repo_tests_expected_failures", []))
                if summary == "failed" and expected_fail:
                    if failing != expected_fail:
                        problems.append(
                            f"designed-failure set mismatch: got {sorted(failing)}, expected {sorted(expected_fail)}")
                elif summary == "failed" and not expected_fail:
                    problems.append(f"UNEXPECTED test failures: {sorted(failing)}")
                elif summary == "ok" and expected_fail:
                    problems.append("expected designed failures but the suite is green")
        if problems:
            failures += 1
            print(f"[FAIL] {cid}:")
            for p in problems:
                print(f"   - {p}")
        else:
            print(f"[OK]   {cid}: schema, anchors, task prompt, repo tests ({'green' if not c.get('repo_tests_expected_failures') else 'with designed failures'})")
    print(f"\n{'FAIL' if failures else 'PASS'}: {failures} case(s) with problems")
    return 1 if failures else 0


def prepare(run_id: str, cases: list[str], variants: list[str], skills_dir: Path,
            ablation_cases: list[str] | None = None) -> int:
    """Prepare work dirs for every (case, variant) pair.

    `variants` may contain ablation variants (ablation-full-minus-*). When
    `ablation_cases` is given, ablation variants are only prepared for those
    case ids (non-ablation variants always cover every selected case).
    """
    run_root = RUNS / run_id
    if run_root.exists():
        print(f"refusing to overwrite existing run dir: {run_root}")
        return 2
    manifest = []
    for d in sorted(FIXTURES.iterdir()):
        cj = d / "case.json"
        if not d.is_dir() or not cj.exists():
            continue
        c = json.loads(_read(cj))
        if cases != ["all"] and c["id"] not in cases:
            continue
        for variant in variants:
            if variant.startswith("ablation-") and ablation_cases is not None \
                    and c["id"] not in ablation_cases:
                continue
            run_dir = run_root / c["id"] / variant
            work = run_dir / "work"
            (run_dir / "out").mkdir(parents=True, exist_ok=True)
            work.mkdir(parents=True, exist_ok=True)
            repo_src = d / c["repo_fixture"]
            shutil.copytree(repo_src, work / "repo", dirs_exist_ok=False)
            _write(run_dir / "task.md", _read(d / c["task_prompt_file"]))
            # baseline commit of the pristine fixture (so executors' commits diff against it)
            _git(["init", "-q", "-b", "main"], work / "repo")
            _git(["-c", "user.name=eval-runner", "-c", "user.email=eval@local",
                  "add", "-A"], work / "repo")
            _git(["-c", "user.name=eval-runner", "-c", "user.email=eval@local",
                  "commit", "-q", "-m", "fixture baseline"], work / "repo")
            # render the variant prompt
            ablation = variant.removeprefix("ablation-") if variant.startswith("ablation-") else None
            if variant in VARIANTS:
                tpl = _read(PROMPTS / f"{variant}.md")
                ablation_block = ""
            else:
                tpl = _read(PROMPTS / "candidate.md")
                ablation_block = ABLATION_TEMPLATE[ablation]
            prompt = (tpl.replace("{task_prompt}", str(run_dir / "task.md"))
                        .replace("{work_dir}", str(work / "repo"))
                        .replace("{plan_out}", str(run_dir / "out"))
                        .replace("{telemetry_file}", str(run_dir / "telemetry.jsonl"))
                        .replace("{skills_dir}", str(skills_dir))
                        .replace("{glossary}", str(skills_dir.parent / "references" / "glossary.md"))
                        .replace("{plan_check}", str(PLAN_CHECK))
                        .replace("{uv_cache}", str(UV_CACHE))
                        .replace("{ablation_block}", ablation_block))
            _write(run_dir / "prompt.md", prompt)
            spec = {
                "run_id": run_id,
                "case_id": c["id"],
                "variant": variant,
                "ablation_remove": ablation,
                "model": {
                    "name": "host-session-model",
                    "note": "all variants run on the same host model/subagent channel; per-run model config is not exposed by the host in V1",
                },
                "run_index": 0,
                "created_at": _now(),
                "skills_dir": str(skills_dir),
                "protocol_version": "1",
                "paths": {
                    "run_dir": str(run_dir),
                    "work_dir": str(work / "repo"),
                    "task_prompt": str(run_dir / "task.md"),
                    "prompt_file": str(run_dir / "prompt.md"),
                    "plan_out": str(run_dir / "out"),
                    "telemetry_file": str(run_dir / "telemetry.jsonl"),
                },
            }
            errs = static_scorer.validate_json_against(spec, SCHEMAS / "run-spec.schema.json")
            if errs:
                print(f"[FAIL] spec for {c['id']}/{variant} does not validate: {errs[:3]}")
                return 1
            _write(run_dir / "spec.json", json.dumps(spec, indent=2, ensure_ascii=False))
            manifest.append({"case_id": c["id"], "variant": variant, "run_dir": str(run_dir)})
            print(f"[prep] {c['id']} / {variant}")
    _write(run_root / "manifest.json", json.dumps(
        {"run_id": run_id, "created_at": _now(), "skills_dir": str(skills_dir),
         "model": spec["model"], "specs": manifest}, indent=2, ensure_ascii=False))
    print(f"\nprepared {len(manifest)} run(s) under {run_root}\n"
          f"next: have the host session execute each run per ORCHESTRATION.md")
    return 0


def _load_timing(run_dir: Path) -> dict | None:
    p = run_dir / "timing.json"
    if not p.exists():
        return None
    try:
        return json.loads(_read(p))
    except json.JSONDecodeError:
        return None


def _e_vector(planning: dict, timing: dict | None, variant: str) -> dict:
    """Planning-phase E vector: measured where measurable, explicit null otherwise
    (bootstrap §2.4 — the raw dimensions are never dropped)."""
    sv = planning.get("structural_validity", {})
    sd = planning.get("scope_discipline", {})
    cl = planning.get("context_locality", {})
    rc = planning.get("recoverability", {})
    if variant in VARIANTS and variant != "candidate":
        success = planning.get("produced") and (planning.get("task_count", {}).get("actual") or 0) >= 3
    else:
        success = (planning.get("produced") and sv.get("lint_exit") == 0
                   and (sv.get("audit_verdict") in ("PASS", None)))
    replans = None
    if sv.get("audit_rounds"):
        replans = max(0, sv["audit_rounds"] - 1)
    return {
        "success": bool(success) if success is not None else None,
        "wall_time": (timing or {}).get("wall_time_seconds"),
        "tokens": None,  # host does not expose per-subagent token usage in V1
        "context_read": cl.get("amplification_proxy"),
        "rework": None,
        "integration_defects": None,
        "scope_creep": len(sd.get("creep_items_planned", [])) if sd else None,
        "replans": replans,
        "compactions": None,  # not observable from the host in V1
        "local_recoverability": rc.get("score"),
    }


def score_run(run_dir: Path) -> dict:
    spec = json.loads(_read(run_dir / "spec.json"))
    plan_out = Path(spec["paths"]["plan_out"])
    case = json.loads(_read(FIXTURES / spec["case_id"] / "case.json"))
    timing = _load_timing(run_dir)
    variant = spec["variant"]

    if variant in VARIANTS or variant.startswith("ablation-"):
        if variant == "candidate" or variant.startswith("ablation-"):
            if (plan_out / "stage-contract.json").exists():
                planning = static_scorer.score_candidate_plan(case, plan_out)
            else:
                planning = {"produced": False, "variant_kind": "structured",
                            "structural_validity": {"lint_exit": None,
                                                    "findings": {"blocker": 0, "major": 0, "minor": 0},
                                                    "audit_verdict": None, "audit_rounds": None},
                            "gaming_flags": [], "judge_pending": [],
                            "metric_coverage": {}, "task_count": {"actual": 0, "range": None, "in_range": None}}
        else:
            text = ""
            for f in sorted(plan_out.glob("*.md")):
                text += f.read_text(encoding="utf-8") + "\n"
            if not text.strip():
                planning = {"produced": False, "variant_kind": "prose",
                            "gaming_flags": [], "judge_pending": [], "metric_coverage": {},
                            "task_count": {"actual": 0, "range": None, "in_range": None}}
            else:
                repo_files = [str(p.relative_to(Path(spec["paths"]["work_dir"])).as_posix())
                              for p in Path(spec["paths"]["work_dir"]).rglob("*")
                              if p.is_file() and ".git" not in p.parts]
                planning = static_scorer.score_prose_plan(case, text, repo_files)
    else:
        raise SystemExit(f"unknown variant {variant}")

    planning.pop("findings", None)
    planning.pop("parse", None)
    e = _e_vector(planning, timing, variant)
    result = {
        "run_id": spec["run_id"],
        "case_id": spec["case_id"],
        "planner_variant": variant,
        "model": spec["model"]["name"],
        "seed_or_run_index": spec.get("run_index"),
        "phase": "planning-only",
        "planning": planning,
        "execution": None,
        "e_vector": e,
        "artifacts": {
            "plan_dir": spec["paths"]["plan_out"],
            "score_file": str(run_dir / "run-result.json"),
            "trace": (str(run_dir / "telemetry.jsonl") if (run_dir / "telemetry.jsonl").exists() else None),
            "diff": None,
            "tests": None,
        },
        "notes": {
            "tokens": "not observable from the host per-subagent in V1 (schema reserved)",
            "compactions": "not observable from the host in V1 (schema reserved)",
        },
    }
    errs = static_scorer.validate_json_against(result, SCHEMAS / "run-result.schema.json")
    if errs:
        print(f"[warn] run-result for {spec['case_id']}/{variant} fails schema: {errs[:3]}")
    return result


def score(run_id: str) -> int:
    run_root = RUNS / run_id
    manifest_p = run_root / "manifest.json"
    if not manifest_p.exists():
        print(f"no manifest at {manifest_p} — run prepare first")
        return 2
    manifest = json.loads(_read(manifest_p))
    bad = 0
    for s in manifest["specs"]:
        run_dir = Path(s["run_dir"])
        res = score_run(run_dir)
        _write(run_dir / "run-result.json", json.dumps(res, indent=2, ensure_ascii=False))
        p = res["planning"]
        sv = p.get("structural_validity", {})
        status = "produced" if p.get("produced") else "MISSING"
        lint = sv.get("lint_exit")
        audit = sv.get("audit_verdict") or "-"
        print(f"[scored] {s['case_id']:38s} {s['variant']:28s} {status:8s} lint={lint} audit={audit} "
              f"e.success={res['e_vector']['success']}")
    print(f"\nscored {len(manifest['specs'])} run(s) under {run_root}")
    return bad


def _diff_stat(work_repo: Path) -> dict:
    # Diff from the root commit (prepare's "fixture baseline" commit) so the
    # stat works regardless of how many commits the executor made.
    root = subprocess.run(["git", "-C", str(work_repo), "rev-list", "--max-parents=0", "HEAD"],
                          capture_output=True, text=True).stdout.strip().splitlines()
    base = root[0] if root else ""
    rng = f"{base}..HEAD" if base else "HEAD"
    r = subprocess.run(["git", "-C", str(work_repo), "log", "--numstat", "--format=", rng],
                       capture_output=True, text=True)
    added = deleted = 0
    files = set()
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            try:
                added += int(parts[0])
                deleted += int(parts[1])
            except ValueError:
                pass
            files.add(parts[2])
    return {"files": sorted(files), "added_lines": added, "deleted_lines": deleted}


def finalize_execution(run_dir: Path) -> int:
    run_dir = Path(run_dir)
    res_p = run_dir / "run-result.json"
    if not res_p.exists():
        print("score the run first (run-result.json missing)")
        return 2
    res = json.loads(_read(res_p))
    spec = json.loads(_read(run_dir / "spec.json"))
    work = Path(spec["paths"]["work_dir"])
    plan_out = Path(spec["paths"]["plan_out"])
    telemetry = []
    if Path(spec["paths"]["telemetry_file"]).exists():
        for line in Path(spec["paths"]["telemetry_file"]).read_text(encoding="utf-8").splitlines():
            try:
                telemetry.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    reads = [t for t in telemetry if t.get("op") == "read"]
    unique_reads = {t.get("path") for t in reads if t.get("path")}
    report = {}
    rep_p = plan_out / "execution-report.json"
    if rep_p.exists():
        try:
            report = json.loads(_read(rep_p))
        except json.JSONDecodeError:
            pass
    diff = _diff_stat(work)
    churn = diff["added_lines"] + diff["deleted_lines"]
    rework_ratio = round((churn - diff["added_lines"]) / max(1, churn), 4) if churn else 0.0
    # tests: re-run the suite for the record
    code, failing, summary, tail = _run_repo_tests(work)
    # checkpoints written
    checkpoints = sorted(p.name for p in (plan_out / "checkpoints").glob("*.json")) if (plan_out / "checkpoints").is_dir() else []
    replans = len(list(plan_out.glob("replan-request*.json"))) + sum(
        1 for cp in checkpoints if "blocked" in _read(plan_out / "checkpoints" / cp).lower())
    wall = None
    max_task = 0.0
    starts, ends = [], []
    for t in report.get("per_task", []):
        try:
            s, e2 = float(t.get("start", 0)), float(t.get("end", 0))
        except (TypeError, ValueError):
            continue
        if e2 > s:
            starts.append(s)
            ends.append(e2)
            max_task = max(max_task, e2 - s)
    if starts and ends:
        wall = max(ends) - min(starts)
    success = (summary == "ok")
    execution = {
        "success": success,
        "wall_time_seconds": wall,
        "critical_path_seconds": None,
        "input_tokens": None,
        "output_tokens": None,
        "unique_files_read": len(unique_reads),
        "files_read": len(reads),
        "files_changed": len(diff["files"]),
        "changed_paths": diff["files"],
        "rework_ratio": rework_ratio,
        "rework_definition": "churn-based: (total added+deleted across commits - net added) / churn; recorded per bootstrap §7",
        "integration_defects": int(report.get("integration_defects", 0)),
        "scope_creep_items": len(res["planning"].get("scope_discipline", {}).get("creep_items_planned", [])),
        "replans": replans,
        "compactions": None,
        "max_task_duration_seconds": max_task or None,
        "per_task": report.get("per_task", []),
        "tests": {"passed": None, "failed": len(failing), "failing_tests": sorted(failing),
                  "exit_code": code, "tail": tail[-400:]},
        "checkpoints_written": checkpoints,
        "telemetry_note": "file reads are self-reported by the executor per the protocol; token/compaction telemetry is not exposed by the host in V1",
    }
    res["execution"] = execution
    res["phase"] = "planning+execution"
    e = res["e_vector"]
    e["success"] = success
    e["context_read"] = execution["unique_files_read"]
    e["rework"] = rework_ratio
    e["integration_defects"] = execution["integration_defects"]
    e["scope_creep"] = execution["scope_creep_items"]
    e["replans"] = replans
    e["local_recoverability"] = (1.0 if checkpoints and success else (0.5 if checkpoints else None))
    if wall:
        e["wall_time"] = round((e.get("wall_time") or 0.0) + wall, 1)
    res["artifacts"]["diff"] = str(work / ".git")
    res["artifacts"]["tests"] = str(plan_out / "execution-report.json")
    _write(res_p, json.dumps(res, indent=2, ensure_ascii=False))
    print(f"[finalize] {res['case_id']}/{res['planner_variant']}: success={success} "
          f"files_changed={execution['files_changed']} rework={rework_ratio} "
          f"checkpoints={len(checkpoints)} failing_tests={sorted(failing) or 'none'}")
    return 0


def report(run_id: str) -> int:
    run_root = RUNS / run_id
    results = []
    for p in sorted(run_root.rglob("run-result.json")):
        results.append(json.loads(_read(p)))
    if not results:
        print("no run-result.json files found — score the runs first")
        return 2
    REPORTS.mkdir(parents=True, exist_ok=True)
    md, js = aggregate.write_report(run_id, results, REPORTS)
    print(f"report: {md}\njson:   {js}\nruns:   {len(results)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-cases")
    sub.add_parser("validate-fixtures")
    p = sub.add_parser("prepare")
    p.add_argument("--run-id", required=True)
    p.add_argument("--cases", default="all")
    p.add_argument("--variants", default=",".join(VARIANTS))
    p.add_argument("--ablations", default="")
    p.add_argument("--ablation-cases", default="",
                   help="comma-separated case ids that get the ablation variants "
                        "(default: every selected case)")
    p.add_argument("--skills-dir", default=str(SKILLS_DEFAULT))
    p = sub.add_parser("score")
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("finalize-execution")
    p.add_argument("--run-dir", required=True)
    p = sub.add_parser("report")
    p.add_argument("--run-id", required=True)
    args = ap.parse_args()

    if args.cmd == "list-cases":
        return list_cases()
    if args.cmd == "validate-fixtures":
        return validate_fixtures()
    if args.cmd == "prepare":
        cases = ["all"] if args.cases == "all" else [c.strip() for c in args.cases.split(",") if c.strip()]
        variants = [v.strip() for v in args.variants.split(",") if v.strip()]
        abls = [f"ablation-{a.strip()}" for a in args.ablations.split(",") if a.strip()]
        for a in abls:
            if a.removeprefix("ablation-") not in ABLATION_TEMPLATE:
                print(f"unknown ablation {a}; available: {ABLATIONS}")
                return 2
        abl_cases = None
        if args.ablation_cases:
            abl_cases = [x.strip() for x in args.ablation_cases.split(",") if x.strip()]
        return prepare(args.run_id, cases, variants + abls, Path(args.skills_dir),
                       ablation_cases=abl_cases)
    if args.cmd == "score":
        return score(args.run_id)
    if args.cmd == "finalize-execution":
        return finalize_execution(args.run_dir)
    if args.cmd == "report":
        return report(args.run_id)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
