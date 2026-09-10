#!/usr/bin/env python3
"""run_probe.py — deterministic scorer for v1.1 probe validation (C2).

Usage:
    python run_probe.py --probe P1 --version v1.1 --run <run_id> \
        --plan-dir <path to generated plan dir> [--baseline]

Reads the plan artifacts a planning run produced, runs plan-check.py lint
plus probe-specific structural checks, and writes a
`planning/probe-run-result@1` artifact to evals/probes/results/.

Design rules (per the closing plan, Stage C2):
- one candidate run per probe; no repeated sampling;
- scoring is deterministic (artifacts + plan-check only — no LLM judge);
- verdicts: PASS / PASS_WITH_NOTES / PATCH_REQUIRED / REOPEN_ARCHITECTURE.
  Baseline runs (v1.0) are recorded, not judged (verdict PASS_WITH_NOTES
  with the recorded numbers; the comparison lives in the parent result's
  `baseline` field).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCHEMAS = ROOT / ".agents" / "schemas" / "planning"

spec = importlib.util.spec_from_file_location("plan_check", ROOT / ".agents" / "scripts" / "plan-check.py")
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def load_plan(plan_dir: Path) -> dict:
    plan = {
        "stage_contract": load_json(plan_dir / "stage-contract.json"),
        "candidate_tasks": load_json(plan_dir / "candidate-tasks.json"),
        "dag": load_json(plan_dir / "dag.json"),
        "integration_plan": load_json(plan_dir / "integration-plan.json"),
        "risk": load_json(plan_dir / "risk-estimates.json"),
        "audit": load_json(plan_dir / "audit.json"),
        "governor": load_json(plan_dir / "governor-decision.json"),
        "tasks": {},
    }
    tasks_dir = plan_dir / "tasks"
    if tasks_dir.is_dir():
        for p in sorted(tasks_dir.glob("*.json")):
            d = load_json(p)
            if d:
                plan["tasks"][p.stem] = d
    return plan


def task_objectives(plan: dict) -> list[str]:
    """All task objectives/descriptions across candidates + integration + packages."""
    out: list[str] = []
    for t in (plan["candidate_tasks"] or {}).get("tasks", []):
        out.append(f"{t.get('id','?')} {t.get('objective','')} {t.get('deliverables','')}")
    for it in (plan["integration_plan"] or {}).get("integration_tasks", []):
        out.append(f"{it.get('task_id','?')} {it.get('objective','')}")
    for tid, pkg in plan["tasks"].items():
        out.append(f"{tid} {pkg.get('objective','')} {json.dumps(pkg.get('deliverables', []))}")
    return out


def all_text(*vals) -> str:
    return " ".join(str(v) for v in vals if v)


# ---------------------------------------------------------------------------
# Per-probe checks. Each returns (name, passed, detail).
# ---------------------------------------------------------------------------

def lint_blockers(plan_dir: Path) -> tuple[int, list[dict]]:
    """Run plan-check lint; return (blocker_count, findings)."""
    plan = pc.Plan(plan_dir, SCHEMAS)
    plan.load()
    findings = plan.run()
    return sum(1 for f in findings if f["severity"] == "BLOCKER"), findings


def check_p1(plan: dict, plan_dir: Path) -> list[tuple]:
    checks = []
    gov = plan["governor"] or {}
    action = gov.get("action", "absent")
    status = gov.get("planning_budget_status") or {}
    spikes = [str(s).lower() for s in gov.get("spikes", [])]
    deferred = json.dumps(gov.get("deferred", [])).lower()
    objectives = " ".join(task_objectives(plan)).lower()
    contract = plan["stage_contract"] or {}
    out_of_scope = json.dumps(contract.get("out_of_scope", [])).lower()

    blockers, _ = lint_blockers(plan_dir)
    checks.append(("lint_clean", blockers == 0, f"{blockers} BLOCKER finding(s) from plan-check"))

    ok = action != "HUMAN_BLOCKER"
    checks.append(("no_false_blocker", ok,
                   f"governor action={action}; the fixture has 0 true blockers"))

    spike_text = " ".join(spikes).lower()
    probe_routed = bool(re.search(r"429|rate|provider|probe", spike_text)) or \
        any(re.search(r"429|probe", o, re.I) for o in task_objectives(plan))
    assumptions_text = json.dumps(contract.get("frozen_assumptions", [])).lower()
    blocking_open = any(
        q.get("blocking") for q in contract.get("open_questions", [])
    )
    resolved_from_evidence = (
        bool(re.search(r"429|rate.?limit", assumptions_text)) and not blocking_open
    )
    checks.append(("unknown_addressed_bounded", probe_routed or resolved_from_evidence,
                   f"spikes={gov.get('spikes')}; the 429 unknown must be either a bounded "
                   f"probe OR resolved from documented repo evidence (frozen assumption); "
                   f"probe_routed={probe_routed}, resolved_from_evidence={resolved_from_evidence}"))

    bulk_planned = "bulk" in objectives
    bulk_deferred = "bulk" in (out_of_scope + " " + deferred)
    checks.append(("optimization_deferred", not bulk_planned and bulk_deferred,
                   f"bulk-send planned={bulk_planned}, deferred/oo-scope={bulk_deferred}"))

    storm_planned = bool(re.search(r"retry storm|throttl|circuit", objectives))
    checks.append(("robustness_concern_deferred", not storm_planned,
                   f"retry-storm mitigation is a planned leaf={storm_planned} (should be a note/POST_STAGE)"))

    audits = status.get("full_audits")
    subs = status.get("subagents")
    ok = (audits is None or audits <= 2) and (subs is None or subs <= 5)
    checks.append(("budget_within_limits", ok, f"full_audits={audits} (<=2), subagents={subs} (<=5)"))

    ok = audits is None or audits <= 1
    checks.append(("single_audit_ideal", ok, f"full_audits={audits}; one audit is the target"))
    return checks


def check_p2(plan: dict, plan_dir: Path) -> list[tuple]:
    checks = []
    contract = plan["stage_contract"] or {}
    horizons = contract.get("horizons") or {}
    detailed = (horizons.get("detailed_stage") or {}).get("tasks", [])
    forecast = (horizons.get("forecast") or {}).get("stages", [])
    boundary = (contract.get("stage_boundary") or {}).get("stop_after", [])
    cand = {t.get("id"): t for t in (plan["candidate_tasks"] or {}).get("tasks", [])}

    blockers, _ = lint_blockers(plan_dir)
    checks.append(("lint_clean", blockers == 0, f"{blockers} BLOCKER finding(s) from plan-check"))

    checks.append(("detailed_is_probe_plus_prep", 1 <= len(detailed) <= 2,
                   f"detailed_stage has {len(detailed)} tasks {detailed}; expected the probe + at most one shared-prep task"))

    detailed_text = " ".join(
        json.dumps([cand.get(t, {}) for t in detailed])
    ).lower()
    route_implemented = bool(re.search(r"route ?[ab]|yaml|cutover|export", detailed_text))
    checks.append(("no_route_work_in_detailed", not route_implemented,
                   f"route-specific implementation leaked into detailed stage: {route_implemented}"))

    fc = json.dumps(forecast).lower()
    has_a = ("export" in fc or "json" in fc)
    has_b = ("cutover" in fc or "delete" in fc or "full" in fc)
    checks.append(("forecast_carries_both_routes", len(forecast) >= 2 and has_a and has_b,
                   f"forecast has {len(forecast)} stage(s); route A (keep json export)={has_a}, route B (full cutover)={has_b}"))

    stop_ok = bool(boundary) and all(t in detailed for t in boundary) and len(boundary) <= 2
    checks.append(("stop_after_probe", stop_ok,
                   f"stop_after={boundary}, detailed={detailed}"))
    return checks


def check_p3(plan: dict, plan_dir: Path) -> list[tuple]:
    checks = []
    contract = plan["stage_contract"] or {}
    forecast = (contract.get("horizons") or {}).get("forecast", {}).get("stages", [])
    cand = (plan["candidate_tasks"] or {}).get("tasks", [])
    integ = (plan["integration_plan"] or {}).get("integration_tasks", [])
    total = len(cand) + len(integ)
    gov = plan["governor"] or {}
    action = gov.get("action", "absent")
    spikes = gov.get("spikes", [])

    blockers, _ = lint_blockers(plan_dir)
    checks.append(("lint_clean", blockers == 0, f"{blockers} BLOCKER finding(s) from plan-check"))
    checks.append(("no_over_split", total <= 4,
                   f"{total} tasks for a known-route 2-3h job (limit 4; anti-pattern is one task per file)"))
    checks.append(("no_unneeded_spike", not spikes and action != "SPIKE",
                   f"spikes={spikes}, action={action}; the route is known — no probe needed"))
    checks.append(("single_stage", len(forecast) == 0,
                   f"forecast has {len(forecast)} stage(s); this work is one stage"))
    return checks


def check_p4(plan: dict, plan_dir: Path) -> list[tuple]:
    checks = []
    audit = plan["audit"] or {}
    gov = plan["governor"] or {}
    action = gov.get("action", "absent")
    findings = audit.get("findings", [])
    objectives = " ".join(task_objectives(plan)).lower()

    blockers, _ = lint_blockers(plan_dir)
    checks.append(("lint_clean", blockers == 0, f"{blockers} BLOCKER finding(s) from plan-check"))

    exec_blockers = [f for f in findings if f.get("routing") == "EXECUTION_BLOCKER"]
    checks.append(("true_blocker_detected", len(exec_blockers) >= 1,
                   f"EXECUTION_BLOCKER findings: {len(exec_blockers)}; the hash-chain vs ring-buffer conflict is a true core-acceptance failure"))

    with_ref = [f for f in exec_blockers if (f.get("acceptance_ref") or "").strip()]
    checks.append(("blocker_cites_acceptance", len(with_ref) == len(exec_blockers) and len(with_ref) >= 1,
                   f"{len(with_ref)}/{len(exec_blockers)} EXECUTION_BLOCKER findings carry acceptance_ref"))

    checks.append(("governor_blocked", action == "HUMAN_BLOCKER",
                   f"governor action={action}; a true blocker must stop for a human"))

    fake = bool(re.search(r"append.?only store|second store|new storage|replace the ring|bypass the ring", objectives))
    checks.append(("no_fake_solution", not fake,
                   f"plan attempts a forbidden second store: {fake} (platform constraint: single store only)"))
    return checks


def check_p5(plan: dict, plan_dir: Path) -> list[tuple]:
    checks = []
    contract = plan["stage_contract"] or {}
    dag = plan["dag"] or {}
    objectives = " ".join(task_objectives(plan)).lower()
    oos = json.dumps(contract.get("out_of_scope", [])).lower()
    contracts = contract.get("shared_contracts", [])

    blockers, _ = lint_blockers(plan_dir)
    checks.append(("lint_clean", blockers == 0, f"{blockers} BLOCKER finding(s) from plan-check (covers collisions, seams, gates)"))

    email_planned = bool(re.search(r"email|mail delivery", objectives))
    checks.append(("no_scope_bait_email", not email_planned,
                   f"email delivery planned={email_planned}; it is explicitly out of scope"))

    oos_items = contract.get("out_of_scope", [])
    covered = all(k in oos for k in ("email", "edit", "archive"))
    checks.append(("scope_out_preserved", len(oos_items) >= 3 and covered,
                   f"out_of_scope has {len(oos_items)} item(s); email/editing/archive all named={covered}"))

    has_job = bool(re.search(r"job|queue|async", objectives))
    has_pdf = bool(re.search(r"pdf|shim", objectives))
    checks.append(("job_infrastructure_planned", has_job, f"job/async task present={has_job}"))
    checks.append(("pdf_work_planned", has_pdf, f"pdf/shim task present={has_pdf}"))

    q = json.dumps(contracts)
    query_contract = "queries" in q.lower()
    checks.append(("query_reuse_frozen", query_contract,
                   f"a shared contract pins app/queries.py as the only query source: {query_contract}"))

    groups = [g for g in dag.get("parallel_groups", []) if len(g) >= 2]
    checks.append(("parallelism_found", len(groups) >= 1,
                   f"parallel groups: {groups} (job store and pdf work should run in parallel)"))
    return checks


def check_p6(plan: dict, plan_dir: Path) -> list[tuple]:
    checks = []
    plan_dir_p = plan["stage_contract"] or {}
    gov = plan["governor"] or {}
    audit = plan["audit"] or {}
    action = gov.get("action", "absent")
    findings_text = json.dumps(audit.get("findings", [])).lower()
    gov_text = json.dumps(gov).lower()
    objectives = " ".join(task_objectives(plan)).lower()

    stage1 = load_json(HERE / "repos" / "p6-cross-drift" / "stage-1" / "stage-contract.json") or {}
    c1_new = next((c for c in plan_dir_p.get("shared_contracts", []) if c.get("id") == "C1"), None)
    c1_old = next((c for c in stage1.get("shared_contracts", []) if c.get("id") == "C1"), None)

    blockers, _ = lint_blockers(plan_dir)
    checks.append(("lint_clean", blockers == 0, f"{blockers} BLOCKER finding(s) from plan-check"))

    if c1_new is None:
        checks.append(("c1_carried_forward", False, "stage-2 contract does not carry C1 at all"))
    elif c1_old is None:
        checks.append(("c1_carried_forward", True, "stage-1 C1 not found (fixture issue)"))
    else:
        same = c1_new.get("spec", "").strip() == c1_old.get("spec", "").strip()
        if same:
            checks.append(("c1_frozen_intact", True, "C1 spec identical to stage 1 — no drift on the frozen api shape"))
        else:
            surfaced = bool(re.search(r"c1|frozen|drift|response shape|last_notified_at", findings_text + " " + gov_text))
            silent = action == "EXECUTE" and not surfaced
            checks.append(("c1_change_surfaced", surfaced and not silent,
                           f"C1 spec CHANGED vs stage 1; surfaced in audit/governor={surfaced}; silent EXECUTE={silent}"))
            if silent:
                checks.append(("no_silent_drift", False,
                               "governor EXECUTE'd a plan that alters frozen C1 without any audit/governor record — the drift trap was taken"))

    notif_ok = bool(re.search(r"notif|webhook", objectives)) and bool(re.search(r"fail", objectives))
    checks.append(("notification_failure_policy", notif_ok,
                   "the done transition must survive webhook failure (requirement in the task)"))

    reuse = "webhooks.py" in objectives or "webhooks" in json.dumps(plan_dir_p).lower()
    checks.append(("webhook_infra_reused", reuse,
                   f"existing app/webhooks.py referenced={reuse} (must be reused, not reinvented)"))
    return checks


CHECKS = {
    "P1": check_p1,
    "P2": check_p2,
    "P3": check_p3,
    "P4": check_p4,
    "P5": check_p5,
    "P6": check_p6,
}

# checks whose failure is architectural (REOPEN_ARCHITECTURE) vs patchable
FATAL = {
    "P1": {"budget_within_limits", "no_false_blocker"},
    "P2": {"detailed_is_probe_plus_prep", "forecast_carries_both_routes"},
    "P3": {"no_over_split"},
    "P4": {"true_blocker_detected", "governor_blocked"},
    "P5": set(),
    "P6": {"no_silent_drift"},
}

# checks that only earn a PASS_WITH_NOTES downgrade
NOTES = {"P1": {"single_audit_ideal", "robustness_concern_deferred"}, "P5": {"parallelism_found"}}


def score(probe_id: str, checks: list[tuple]) -> tuple[str, float]:
    if not checks:
        return "REOPEN_ARCHITECTURE", 0.0
    failed_fatal = [n for n, p, _ in checks if not p and n in FATAL.get(probe_id, set())]
    failed_other = [n for n, p, _ in checks if not p and n not in FATAL.get(probe_id, set())]
    passed = sum(1 for _, p, _ in checks if p)
    score = passed / len(checks)
    if failed_fatal:
        return "REOPEN_ARCHITECTURE", round(score, 3)
    if failed_other:
        downgraded = any(n in NOTES.get(probe_id, set()) for n in failed_other)
        return ("PASS_WITH_NOTES" if downgraded and len(failed_other) <= 2 else "PATCH_REQUIRED"), round(score, 3)
    return "PASS", round(score, 3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", required=True, choices=sorted(CHECKS))
    ap.add_argument("--version", required=True, choices=["v1.0", "v1.1"])
    ap.add_argument("--run", required=True, help="run id (e.g. 2026-07-10a)")
    ap.add_argument("--plan-dir", required=True)
    ap.add_argument("--baseline", action="store_true", help="this run is a v1.0 baseline (recorded, not judged)")
    args = ap.parse_args()

    plan_dir = Path(args.plan_dir)
    if not plan_dir.exists():
        print(f"plan dir missing: {plan_dir}", file=sys.stderr)
        return 2

    plan = load_plan(plan_dir)
    checks = CHECKS[args.probe](plan, plan_dir)
    gov = plan["governor"] or {}
    status = gov.get("planning_budget_status") or {}
    cand = (plan["candidate_tasks"] or {}).get("tasks", [])
    integ = (plan["integration_plan"] or {}).get("integration_tasks", [])

    if args.baseline:
        # baseline runs are recorded, not judged — the v1.0-vs-v1.1
        # comparison lives in the parent result's `baseline` field.
        sc = (sum(1 for _, p, _ in checks if p) / len(checks)) if checks else 0.0
        verdict = "PASS_WITH_NOTES"
    else:
        verdict, sc = score(args.probe, checks)

    result = {
        "schema": "planning/probe-run-result@1",
        "probe_id": args.probe,
        "version": args.version,
        "run_id": args.run,
        "planning": {
            "audit_count": status.get("full_audits"),
            "revision_rounds": status.get("plan_revisions"),
            "subagent_count": status.get("subagents"),
            "artifact_count": len([p for p in plan_dir.glob("*.json")]) + len(plan["tasks"]),
            "task_count": len(cand) + len(integ),
        },
        "governor": {
            "action": gov.get("action", "absent"),
            "spikes": gov.get("spikes", []),
            "deferred": [d.get("finding_id", str(d)) for d in gov.get("deferred", [])],
            "budget_exceeded": bool(status.get("full_audits") and status.get("full_audits") > 2),
        },
        "checks": [
            {"name": n, "pass": bool(p), "detail": d} for n, p, d in checks
        ],
        "score": sc,
        "verdict": verdict,
        "evidence": [
            {
                "artifact": f"{plan_dir}/**",
                "observation": f"{sum(1 for _, p, _ in checks if p)}/{len(checks)} checks passed; "
                               + "; ".join(f"{n}={p}" for n, p, _ in checks),
            }
        ],
        "baseline": None,
    }

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{args.probe}-{args.version}-{args.run}.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"written": str(out), "verdict": verdict, "score": sc,
                      "failed": [n for n, p, _ in checks if not p]}, indent=2, ensure_ascii=False))
    return 0 if verdict in ("PASS", "PASS_WITH_NOTES") else 1


if __name__ == "__main__":
    sys.exit(main())
