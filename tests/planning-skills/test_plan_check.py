"""Behavioral tests for plan-check.py itself: the gate must catch planted
defects with the right finding codes, and the validator must reject
schema-invalid artifacts. These encode the deterministic guarantees the
skills promise (fail-closed, specific codes, no silent passes)."""

import importlib.util
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PC = ROOT / ".agents" / "scripts" / "plan-check.py"
SCHEMAS = ROOT / ".agents" / "schemas" / "planning"
FIX = HERE / "fixtures"


def _load_pc():
    spec = importlib.util.spec_from_file_location("plan_check", PC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pc = _load_pc()


def _e(a, b):
    return {"from": a, "to": b, "type": "data", "reason": "test"}


def _lint(plan_dir):
    plan = pc.Plan(Path(plan_dir), SCHEMAS)
    plan.load()
    return plan, plan.run()


def _codes(findings):
    return {f["code"] for f in findings}


def run():
    problems = []

    # ---- graph helpers (unit) ----
    if not pc.has_cycle(["A", "B"], [_e("A", "B"), _e("B", "A")]):
        problems.append("has_cycle missed a 2-cycle")
    if pc.has_cycle(["A", "B", "C"], [_e("A", "B"), _e("B", "C")]):
        problems.append("has_cycle false positive on a DAG")
    # longest_path_hops returns the node count of the longest chain
    if pc.longest_path_hops(["A", "B", "C"], [_e("A", "B"), _e("B", "C"), _e("A", "C")]) != 3:
        problems.append("longest_path_hops: A->B->C expected 3 nodes")
    reach = pc.reachability(["A", "B", "C"], [_e("A", "B"), _e("B", "C")])
    if "C" not in reach.get("A", set()):
        problems.append("reachability: A should reach C transitively")

    # ---- good-plan fixture: clean ----
    plan, findings = _lint(FIX / "good-plan")
    for f in findings:
        problems.append(f"good-plan: unexpected finding {f['severity']} {f['code']} {f['detail'][:60]}")

    # ---- bad-plan fixture: every planted defect must produce its code ----
    bplan, bfindings = _lint(FIX / "bad-plan")
    got = _codes(bfindings)
    expected = {
        "DAG_CYCLE",                 # T01 -> T04 -> T01
        "DAG_UNKNOWN_TASK",          # edge to T99
        "OWNERSHIP_COLLISION_PARALLEL",  # T01 & T02 both own app/shared.py, unordered
        "CONTRACT_UNKNOWN",          # T03 consumes C9
        "NO_INTEGRATION_GATE",       # only contract_consistency task, no e2e/acceptance
        "OPEN_BLOCKING_QUESTION",    # Q1 blocking with empty resolution
        "MISSING_TASK_PACKAGE",      # T03 candidate without tasks/T03.json
        "VAGUE_ACCEPTANCE",          # A1 "works correctly under all conditions"
        "AUDIT_VERDICT_MISMATCH",    # audit PASS while BLOCKER findings exist
    }
    if "SCHEMA_INVALID" in got:
        problems.append(f"bad-plan: schema errors (defects must be schema-legal): "
                        f"{[f['detail'] for f in bfindings if f['code'] == 'SCHEMA_INVALID'][:3]}")
    for code in sorted(expected - got):
        problems.append(f"bad-plan: expected finding code {code} not produced; got {sorted(got)}")

    # severities of the hard gates
    sev = {f["code"]: f["severity"] for f in bfindings}
    for code in ("DAG_CYCLE", "DAG_UNKNOWN_TASK", "OWNERSHIP_COLLISION_PARALLEL",
                 "NO_INTEGRATION_GATE", "OPEN_BLOCKING_QUESTION", "MISSING_TASK_PACKAGE",
                 "AUDIT_VERDICT_MISMATCH"):
        if sev.get(code) != "BLOCKER":
            problems.append(f"bad-plan: {code} should be BLOCKER, got {sev.get(code)}")
    if sev.get("CONTRACT_UNKNOWN") != "MAJOR":
        problems.append(f"bad-plan: CONTRACT_UNKNOWN should be MAJOR, got {sev.get('CONTRACT_UNKNOWN')}")
    if sev.get("VAGUE_ACCEPTANCE") != "MINOR":
        problems.append(f"bad-plan: VAGUE_ACCEPTANCE should be MINOR, got {sev.get('VAGUE_ACCEPTANCE')}")

    # ---- validator rejects tampered artifacts (schema-invalid) ----
    tampered = FIX / "tampered"
    if tampered.exists():
        shutil.rmtree(tampered)
    try:
        shutil.copytree(FIX / "good-plan", tampered)
        dag = tampered / "dag.json"
        data = json.loads(dag.read_text(encoding="utf-8"))
        data.pop("edges")  # required field removed
        dag.write_text(json.dumps(data), encoding="utf-8")
        res = pc.validate_file(dag, SCHEMAS)
        if res["ok"]:
            problems.append("validate_file accepted a dag.json with required 'edges' removed")
        else:
            print(f"note: tamper correctly rejected: {res['errors'][0][:70]}")
        sc = json.loads((tampered / "stage-contract.json").read_text(encoding="utf-8"))
        sc["schema"] = "planning/stage-contract@999"
        (tampered / "stage-contract.json").write_text(json.dumps(sc), encoding="utf-8")
        res2 = pc.validate_file(tampered / "stage-contract.json", SCHEMAS)
        if res2["ok"]:
            problems.append("validate_file accepted a wrong schema const version")
    finally:
        shutil.rmtree(tampered, ignore_errors=True)

    for p in problems:
        print(f"FAIL: {p}")
    if not problems:
        print("PASS: graph helpers, good-plan clean, bad-plan planted defects all "
              f"detected ({len(expected)} codes), validator rejects tampered artifacts")
    return len(problems)


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
