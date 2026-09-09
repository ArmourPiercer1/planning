"""Round-2 structural-fix tests (A-F).

Proves the four targeted fixes closed their semantics on the deterministic
layer:

  A. Stage Contract holds no task ids (logical owners/participants only);
     rebinding a contract to a different task = edit dag.json only, the
     stage contract file is untouched and the plan re-checks consistently.
  B. Snapshot import edges surface as HIDDEN_DEPENDENCY: >= MAJOR for a
     one-hop import not in the leaf's context, BLOCKER when the import target
     is a known shared file.
  C. A task package whose inlined contract spec no longer matches the current
     stage contract => STALE_CONTRACT_SNAPSHOT BLOCKER (spec drift and
     source-hash drift both detected).
  D. merged_kinds is a valid satisfaction path: a merged kind passes schema,
     plan-check (no INTEGRATION_KIND_MISSING / NO_INTEGRATION_GATE), and a
     self-merge is flagged INVALID_INTEGRATION_MERGE.
  E. A legitimately omitted kind (seam_integration, no new wiring) is
     satisfied: no HIDDEN_INTEGRATION_WORK, no INTEGRATION_KIND_MISSING.
  F. Omitting seam_integration while a leaf creates new files next to another
     leaf's existing code (new wiring exists) => HIDDEN_INTEGRATION_WORK
     BLOCKER; moving the new file to a fresh directory makes the omission
     legitimate again.

Fixtures: good-plan/ (clean by construction) and grounded-plan/ (planted
hidden dependencies + hidden integration work, grounded in the real
grounded-repo/ directory via a script-generated snapshot).
"""

import importlib.util
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PC = ROOT / ".agents" / "scripts" / "plan-check.py"
SCHEMAS = ROOT / ".agents" / "schemas" / "planning"
GOOD = HERE / "fixtures" / "good-plan"
GROUNDED = HERE / "fixtures" / "grounded-plan"
TMP = HERE / "tmp-round2"

CONTRACT_CODES = {
    "UNBOUND_CONTRACT", "UNBOUND_SEAM", "CONTRACT_OWNER_TASK_ID",
    "SEAM_PARTICIPANT_TASK_ID", "CONTRACT_CONSUMED_BEFORE_OWNER", "CONTRACT_UNKNOWN",
}


def _load_pc():
    spec = importlib.util.spec_from_file_location("plan_check", PC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pc = _load_pc()


def _plan_dir(src: Path, name: str) -> Path:
    TMP.mkdir(exist_ok=True)
    d = TMP / name
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(src, d)
    return d


def _lint(plan_dir: Path):
    plan = pc.Plan(plan_dir, SCHEMAS)
    plan.load()
    return plan.run()


def _codes(findings):
    return {(f["code"], f["severity"]) for f in findings}


def _mutate(plan_dir: Path, fname: str, fn):
    p = plan_dir / fname
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_a_task_ids_and_rebind(failures: list) -> None:
    # A1: task ids in the stage contract are BLOCKERs (contract + seam)
    d = _plan_dir(GOOD, "a-taskids")

    def m(data):
        for c in data["shared_contracts"]:
            c["logical_owner"] = "T01"
        for s in data["integration_seams"]:
            s["participants"] = ["T01", "T02"]

    _mutate(d, "stage-contract.json", m)
    findings = _lint(d)
    codes = _codes(findings)
    if ("CONTRACT_OWNER_TASK_ID", "BLOCKER") not in codes:
        failures.append(f"A1: expected CONTRACT_OWNER_TASK_ID BLOCKER, got {sorted(codes)}")
    if ("SEAM_PARTICIPANT_TASK_ID", "BLOCKER") not in codes:
        failures.append(f"A1: expected SEAM_PARTICIPANT_TASK_ID BLOCKER, got {sorted(codes)}")

    # A2: rebind C2's owner T02 -> T01 by editing dag.json ONLY. The stage
    # contract bytes are untouched, no contract-structure finding appears,
    # and the only consequence is the (correct) MINOR unlock declaration for
    # T02's now-parallel consumption of frozen C2.
    d = _plan_dir(GOOD, "a-rebind")
    sc_before = (d / "stage-contract.json").read_bytes()

    def m2(data):
        for b in data["contract_bindings"]:
            if b["contract_id"] == "C2":
                b["owner_task"] = "T01"
                b["consumer_tasks"] = ["T01", "T03"]

    _mutate(d, "dag.json", m2)
    findings = _lint(d)
    if (d / "stage-contract.json").read_bytes() != sc_before:
        failures.append("A2: rebind modified stage-contract.json (must be a dag.json-only edit)")
    codes = _codes(findings)
    if codes & {c for c in CONTRACT_CODES}:
        failures.append(f"A2: rebind produced contract-structure findings: {sorted(codes & CONTRACT_CODES)}")
    if codes != {("UNLOCK_NOT_DECLARED", "MINOR")}:
        failures.append(f"A2: expected exactly UNLOCK_NOT_DECLARED MINOR after rebind, got {sorted(codes)}")


def test_b_snapshot_hidden_dependency(failures: list) -> None:
    # B1: grounded-plan T01 extends profiles.py without declaring its one-hop
    # imports: runtime_state.py (known shared file -> BLOCKER) and
    # schema.py (single importer -> MAJOR).
    findings = _lint(GROUNDED)
    hd = [f for f in findings if f["code"] == "HIDDEN_DEPENDENCY" and f["task_id"] == "T01"]
    if not any(f["severity"] == "BLOCKER" and "app/runtime_state.py" in f["detail"] for f in hd):
        failures.append(f"B1: expected BLOCKER HIDDEN_DEPENDENCY on app/runtime_state.py, got "
                        f"{[(f['severity'], f['detail'][:60]) for f in hd]}")
    if not any(f["severity"] == "MAJOR" and "app/schema.py" in f["detail"] for f in hd):
        failures.append(f"B1: expected MAJOR HIDDEN_DEPENDENCY on app/schema.py, got "
                        f"{[(f['severity'], f['detail'][:60]) for f in hd]}")

    # B2: declaring the imports removes every HIDDEN_DEPENDENCY.
    d = _plan_dir(GROUNDED, "b-declared")

    def m(data):
        for t in data["tasks"]:
            if t["id"] == "T01":
                t["required_context"]["files"] += [
                    "app/runtime_state.py (existing, read-only)",
                    "app/schema.py (existing, read-only)",
                    "app/api/__init__.py (existing, read-only)",
                ]

    _mutate(d, "candidate-tasks.json", m)
    hd2 = [f for f in _lint(d) if f["code"] == "HIDDEN_DEPENDENCY"]
    if hd2:
        failures.append(f"B2: expected zero HIDDEN_DEPENDENCY after declaring imports, got "
                        f"{[(f['severity'], f['detail'][:60]) for f in hd2]}")


def test_c_stale_contract_snapshot(failures: list) -> None:
    # C1: change the C1 spec AFTER packaging -> both inliners go stale.
    d = _plan_dir(GOOD, "c-stale-spec")

    def m1(data):
        for c in data["shared_contracts"]:
            if c["id"] == "C1":
                c["spec"] += " (v2: plus a rate-limit note for batch consumers)"

    _mutate(d, "stage-contract.json", m1)
    stale = [f for f in _lint(d) if f["code"] == "STALE_CONTRACT_SNAPSHOT"]
    if not stale:
        failures.append("C1: expected STALE_CONTRACT_SNAPSHOT BLOCKER after spec change")
    elif not all(f["severity"] == "BLOCKER" for f in stale):
        failures.append(f"C1: STALE_CONTRACT_SNAPSHOT must be BLOCKER, got "
                        f"{[(f['artifact'], f['severity']) for f in stale]}")
    if len(stale) < 2:
        failures.append(f"C1: expected both T01 and T03 packages flagged, got {len(stale)}")

    # C2: identical spec but a wrong source_hash is also stale.
    d = _plan_dir(GOOD, "c-stale-hash")

    def m2(data):
        for fc in data["frozen_contracts"]:
            fc["source_hash"] = "sha256:" + "0" * 64

    _mutate(d, "tasks/T01.json", m2)
    stale2 = [f for f in _lint(d) if f["code"] == "STALE_CONTRACT_SNAPSHOT"
              and f["artifact"] == "tasks/T01.json"]
    if not stale2:
        failures.append("C2: expected STALE_CONTRACT_SNAPSHOT BLOCKER on hash drift")


def test_d_merged_kinds(failures: list) -> None:
    # D1: good-plan already merges final_acceptance into the e2e_closure
    # task — the merged kind must be satisfied (no kind-missing/gate
    # findings) and the plan stays fully clean.
    findings = _lint(GOOD)
    if findings:
        failures.append(f"D1: good-plan (with merged_kinds) must lint clean, got "
                        f"{sorted(_codes(findings))}")
    ip = json.loads((GOOD / "integration-plan.json").read_text(encoding="utf-8"))
    t03 = next(it for it in ip["integration_tasks"] if it["task_id"] == "T03")
    if t03.get("merged_kinds") != ["final_acceptance"] or t03["kind"] != "e2e_closure":
        failures.append(f"D1: fixture precondition broken: {t03}")
    if pc.validate_file(GOOD / "integration-plan.json", SCHEMAS)["ok"] is not True:
        failures.append("D1: integration-plan@2 with merged_kinds must be schema-valid")

    # D2: merging a task's OWN kind is ambiguous and must be flagged.
    d = _plan_dir(GOOD, "d-self-merge")

    def m(data):
        for it in data["integration_tasks"]:
            if it["task_id"] == "T03":
                it["kind"] = "final_acceptance"

    _mutate(d, "integration-plan.json", m)
    findings = _lint(d)
    codes = _codes(findings)
    if ("INVALID_INTEGRATION_MERGE", "MAJOR") not in codes:
        failures.append(f"D2: expected INVALID_INTEGRATION_MERGE MAJOR for self-merge, got {sorted(codes)}")
    if any(sev == "BLOCKER" for _, sev in codes):
        failures.append(f"D2: self-merge variant must not introduce BLOCKERs, got {sorted(codes)}")


def test_e_legitimate_omission(failures: list) -> None:
    # E: good-plan omits seam_integration with justification and has NO new
    # wiring (no leaf creates files next to another leaf's existing code) —
    # the omission is satisfied: no HIDDEN_INTEGRATION_WORK, no
    # INTEGRATION_KIND_MISSING, plan fully clean.
    ip = json.loads((GOOD / "integration-plan.json").read_text(encoding="utf-8"))
    omitted = {o["kind"] for o in ip.get("omitted_kinds", [])}
    if "seam_integration" not in omitted:
        failures.append(f"E: fixture precondition broken: omitted_kinds = {sorted(omitted)}")
    findings = _lint(GOOD)
    bad = [f for f in findings
           if f["code"] in ("HIDDEN_INTEGRATION_WORK", "INTEGRATION_KIND_MISSING",
                            "NO_INTEGRATION_GATE")]
    if bad:
        failures.append(f"E: legitimate omission must produce no integration findings, got "
                        f"{[(f['code'], f['severity']) for f in bad]}")


def test_f_omission_with_new_wiring(failures: list) -> None:
    # F1: grounded-plan omits seam_integration while T02 creates
    # app/cache_layer.py next to T03's existing app/store.py (real new
    # wiring) => HIDDEN_INTEGRATION_WORK BLOCKER.
    findings = _lint(GROUNDED)
    hiw = [f for f in findings if f["code"] == "HIDDEN_INTEGRATION_WORK"]
    if not hiw or hiw[0]["severity"] != "BLOCKER":
        failures.append(f"F1: expected HIDDEN_INTEGRATION_WORK BLOCKER, got "
                        f"{[(f['code'], f['severity']) for f in findings if 'INTEGRATION' in f['code']]}")

    # F2: moving T02's new file into a fresh directory (app/cache/) removes
    # the wiring signal — the same omission becomes legitimate.
    d = _plan_dir(GROUNDED, "f-new-dir")

    def m(data):
        for t in data["tasks"]:
            if t["id"] == "T02":
                t["owned_paths"] = ["app/cache/cache_layer.py"]
                t["required_context"]["files"] = ["app/cache/cache_layer.py (new)"]

    _mutate(d, "candidate-tasks.json", m)
    hiw2 = [f for f in _lint(d) if f["code"] == "HIDDEN_INTEGRATION_WORK"]
    if hiw2:
        failures.append(f"F2: expected no HIDDEN_INTEGRATION_WORK for fresh-directory new files, "
                        f"got {[(f['severity'], f['detail'][:80]) for f in hiw2]}")


def run():
    failures: list = []
    try:
        test_a_task_ids_and_rebind(failures)
        test_b_snapshot_hidden_dependency(failures)
        test_c_stale_contract_snapshot(failures)
        test_d_merged_kinds(failures)
        test_e_legitimate_omission(failures)
        test_f_omission_with_new_wiring(failures)
    finally:
        if TMP.exists():
            shutil.rmtree(TMP, ignore_errors=True)
    for f in failures:
        print(f"FAIL: {f}")
    if not failures:
        print("PASS: A (no task ids + rebind via dag only), B (snapshot import -> "
              "HIDDEN_DEPENDENCY MAJOR/BLOCKER), C (stale inline spec/hash -> BLOCKER), "
              "D (merged_kinds valid; self-merge flagged), E (legitimate omission satisfied), "
              "F (omission with new wiring -> HIDDEN_INTEGRATION_WORK BLOCKER)")
    return len(failures)


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
