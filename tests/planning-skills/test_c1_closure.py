"""C1 closure negative tests: verify the new deterministic enforcement fires."""
import importlib.util, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PC = ROOT / ".agents" / "scripts" / "plan-check.py"
SCHEMAS = ROOT / ".agents" / "schemas" / "planning"
FIX = ROOT / "tests" / "planning-skills" / "fixtures"

spec = importlib.util.spec_from_file_location("plan_check", PC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pc = mod

problems = []
TMP = FIX / "tmp-c1"
if TMP.exists():
    shutil.rmtree(TMP)
TMP.mkdir(parents=True)

try:
    # --- Test 1: stage-contract@3 missing a v1.1 field -> SCHEMA_INVALID ---
    p1 = TMP / "c1-test1"
    shutil.copytree(FIX / "good-plan", p1)
    sc = json.loads((p1 / "stage-contract.json").read_text(encoding="utf-8"))
    sc["schema"] = "planning/stage-contract@3"
    sc["delivery_profile"] = {"level": "alpha"}
    sc["planning_budget"] = {"max_full_audits": 2, "max_plan_revisions": 3, "max_planning_subagents": 5}
    sc["horizons"] = {
        "commitment": {"tasks": ["T01"]},
        "detailed_stage": {"objective": "test", "tasks": ["T01", "T02"]},
        "forecast": {"stages": []},
    }
    # missing stage_boundary and next_planning_trigger -> must fail
    (p1 / "stage-contract.json").write_text(json.dumps(sc), encoding="utf-8")
    res = pc.validate_file(p1 / "stage-contract.json", SCHEMAS)
    if res["ok"]:
        problems.append("T1 FAIL: @3 schema accepted contract missing stage_boundary/next_planning_trigger")
    else:
        print(f"T1 PASS: @3 rejects missing v1.1 fields ({res['errors'][0][:70]})")

    # --- Test 2: complete @3 contract passes, but bad horizons -> HORIZON_SCOPE_VIOLATION ---
    p2 = TMP / "c1-test2"
    shutil.copytree(FIX / "good-plan", p2)
    sc = json.loads((p2 / "stage-contract.json").read_text(encoding="utf-8"))
    sc["schema"] = "planning/stage-contract@3"
    sc["delivery_profile"] = {"level": "alpha"}
    sc["planning_budget"] = {"max_full_audits": 2, "max_plan_revisions": 3, "max_planning_subagents": 5}
    # commitment contains a task NOT in detailed_stage -> violation
    sc["horizons"] = {
        "commitment": {"tasks": ["T99"]},
        "detailed_stage": {"objective": "test", "tasks": ["T01", "T02"]},
        "forecast": {"stages": [{"objective": "future", "depends_on_evidence": ["e1"]}]},
    }
    sc["stage_boundary"] = {"stop_after": ["T01"], "because": "test boundary reason long enough"}
    sc["next_planning_trigger"] = {"normal": ["stage_acceptance_reached"]}
    (p2 / "stage-contract.json").write_text(json.dumps(sc), encoding="utf-8")
    plan = pc.Plan(p2, SCHEMAS)
    plan.load()
    codes = {f["code"] for f in plan.run()}
    if "HORIZON_SCOPE_VIOLATION" not in codes:
        problems.append(f"T2 FAIL: commitment⊄detailed not flagged; got {sorted(codes)}")
    else:
        print("T2 PASS: HORIZON_SCOPE_VIOLATION on commitment-not-subset-of-detailed_stage")

    # --- Test 3: forecast with leaf task ids -> HORIZON_SCOPE_VIOLATION ---
    p3 = TMP / "c1-test3"
    shutil.copytree(FIX / "good-plan", p3)
    sc = json.loads((p3 / "stage-contract.json").read_text(encoding="utf-8"))
    sc["schema"] = "planning/stage-contract@3"
    sc["delivery_profile"] = {"level": "alpha"}
    sc["planning_budget"] = {"max_full_audits": 2, "max_plan_revisions": 3, "max_planning_subagents": 5}
    sc["horizons"] = {
        "commitment": {"tasks": ["T01"]},
        "detailed_stage": {"objective": "test", "tasks": ["T01", "T02"]},
        "forecast": {"stages": [{"objective": "implement T07 later", "depends_on_evidence": ["e1"]}]},
    }
    sc["stage_boundary"] = {"stop_after": ["T01"], "because": "test boundary reason long enough"}
    sc["next_planning_trigger"] = {"normal": ["stage_acceptance_reached"]}
    (p3 / "stage-contract.json").write_text(json.dumps(sc), encoding="utf-8")
    plan = pc.Plan(p3, SCHEMAS)
    plan.load()
    findings = plan.run()
    hz = [f for f in findings if f["code"] == "HORIZON_SCOPE_VIOLATION" and "forecast" in f["detail"]]
    if not hz:
        problems.append("T3 FAIL: forecast leaf task id not flagged")
    else:
        print("T3 PASS: HORIZON_SCOPE_VIOLATION on forecast leaf task reference")

    # --- Test 4: audit@3 EXECUTION_BLOCKER without acceptance_ref ---
    p4 = TMP / "c1-test4"
    shutil.copytree(FIX / "good-plan", p4)
    a = json.loads((p4 / "audit.json").read_text(encoding="utf-8"))
    a["schema"] = "planning/audit@3"
    a["verdict"] = "FAIL"
    a["findings"] = [{
        "id": "F01", "severity": "BLOCKER", "routing": "EXECUTION_BLOCKER",
        "check": "hidden_dependency", "evidence": "planted blocker evidence here",
        "suggested_fix": "fix it", "acceptance_ref": None,
    }]
    (p4 / "audit.json").write_text(json.dumps(a), encoding="utf-8")
    plan = pc.Plan(p4, SCHEMAS)
    plan.load()
    codes = {f["code"] for f in plan.run()}
    if "EXECUTION_BLOCKER_MISSING_REF" not in codes:
        problems.append(f"T4 FAIL: EXECUTION_BLOCKER without acceptance_ref not flagged; got {sorted(codes)}")
    else:
        print("T4 PASS: EXECUTION_BLOCKER_MISSING_REF fires")

    # --- Test 5: governor conflict — EXECUTION_BLOCKER routed but action EXECUTE ---
    p5 = TMP / "c1-test5"
    shutil.copytree(FIX / "good-plan", p5)
    a = json.loads((p5 / "audit.json").read_text(encoding="utf-8"))
    a["schema"] = "planning/audit@3"
    a["verdict"] = "FAIL"
    a["findings"] = [{
        "id": "F01", "severity": "BLOCKER", "routing": "EXECUTION_BLOCKER",
        "check": "hidden_dependency", "evidence": "planted blocker evidence here",
        "suggested_fix": "fix it", "acceptance_ref": "A1",
    }]
    (p5 / "audit.json").write_text(json.dumps(a), encoding="utf-8")
    gov = {
        "schema": "planning/governor-decision@1",
        "action": "EXECUTE",
        "blocking_findings": [],
        "spikes": [],
        "deferred": [],
        "planning_budget_status": {"plan_revisions": 0, "full_audits": 1, "subagents": 2},
        "forbidden_actions": [],
        "reason": "test reason long enough",
    }
    (p5 / "governor-decision.json").write_text(json.dumps(gov), encoding="utf-8")
    plan = pc.Plan(p5, SCHEMAS)
    plan.load()
    codes = {f["code"] for f in plan.run()}
    if "GOVERNOR_CONFLICT" not in codes:
        problems.append(f"T5 FAIL: governor EXECUTE despite EXECUTION_BLOCKER not flagged; got {sorted(codes)}")
    else:
        print("T5 PASS: GOVERNOR_CONFLICT on EXECUTE+EXECUTION_BLOCKER")

    # --- Test 6: governor budget exceeded ---
    p6 = TMP / "c1-test6"
    shutil.copytree(FIX / "good-plan", p6)
    sc = json.loads((p6 / "stage-contract.json").read_text(encoding="utf-8"))
    sc["schema"] = "planning/stage-contract@3"
    sc["delivery_profile"] = {"level": "alpha"}
    sc["planning_budget"] = {"max_full_audits": 2, "max_plan_revisions": 3, "max_planning_subagents": 5}
    sc["horizons"] = {
        "commitment": {"tasks": ["T01"]},
        "detailed_stage": {"objective": "test", "tasks": ["T01", "T02"]},
        "forecast": {"stages": []},
    }
    sc["stage_boundary"] = {"stop_after": ["T01"], "because": "test boundary reason long enough"}
    sc["next_planning_trigger"] = {"normal": ["stage_acceptance_reached"]}
    (p6 / "stage-contract.json").write_text(json.dumps(sc), encoding="utf-8")
    gov = {
        "schema": "planning/governor-decision@1",
        "action": "HUMAN_BLOCKER",
        "blocking_findings": [],
        "spikes": [],
        "deferred": [],
        "planning_budget_status": {"plan_revisions": 0, "full_audits": 3, "subagents": 2},
        "forbidden_actions": ["launch_another_full_audit"],
        "reason": "test reason long enough",
    }
    (p6 / "governor-decision.json").write_text(json.dumps(gov), encoding="utf-8")
    plan = pc.Plan(p6, SCHEMAS)
    plan.load()
    codes = {f["code"] for f in plan.run()}
    if "GOVERNOR_BUDGET_EXCEEDED" not in codes:
        problems.append(f"T6 FAIL: full_audits=3 > max=2 not flagged; got {sorted(codes)}")
    else:
        print("T6 PASS: GOVERNOR_BUDGET_EXCEEDED fires")

    # --- Test 7: legacy @2 and @1 artifacts still validate ---
    ok2 = pc.validate_file(FIX / "good-plan" / "stage-contract.json", SCHEMAS)
    ok1 = pc.validate_file(FIX / "good-plan" / "audit.json", SCHEMAS)
    if not (ok2["ok"] and ok1["ok"]):
        problems.append(f"T7 FAIL: legacy @2 validation broken: {ok2['errors'][:1]} {ok1['errors'][:1]}")
    else:
        print("T7 PASS: legacy @2 artifacts still validate")

    # --- Test 8: schema files are pure per version (no mixed enum files) ---
    # A @3-declared contract must FAIL direct validation against the @2 file,
    # and a @2 contract must FAIL against the @3 file. This is the property a
    # probe run tried to break by turning the @2 file's schema field into
    # enum [@2, @3] — pinned here so it cannot regress.
    v3_contract = json.loads((FIX / "v11-plan" / "stage-contract.json").read_text(encoding="utf-8"))
    v2_contract = json.loads((FIX / "good-plan" / "stage-contract.json").read_text(encoding="utf-8"))
    s2 = json.loads((SCHEMAS / "stage-contract.schema.json").read_text(encoding="utf-8"))
    s3 = json.loads((SCHEMAS / "stage-contract-v3.schema.json").read_text(encoding="utf-8"))
    if v3_contract.get("schema") != "planning/stage-contract@3" or v2_contract.get("schema") != "planning/stage-contract@2":
        problems.append("T8 FAIL: fixture contracts do not declare @3/@2 as expected")
    elif not pc.validate_against(v3_contract, s2):
        problems.append("T8 FAIL: @2 schema file accepted a @3-declared contract (mixed file — C1-A violation)")
    elif not pc.validate_against(v2_contract, s3):
        problems.append("T8 FAIL: @3 schema file accepted a @2 contract (mixed file — C1-A violation)")
    else:
        print("T8 PASS: stage-contract schema files are pure per version")

finally:
    shutil.rmtree(TMP, ignore_errors=True)

for p in problems:
    print(f"FAIL: {p}")
sys.exit(1 if problems else 0)
