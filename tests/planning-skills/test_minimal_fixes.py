"""Targeted tests for the 7 minimal fixes.

Run: uv run --no-project python test_minimal_fixes.py
Uses the good-plan fixture as a base, copying and modifying specific artifacts.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SCHEMAS = ROOT / ".agents" / "schemas" / "planning"
FIXTURE = HERE / "fixtures" / "good-plan"

WORK = HERE / "tmp-minfix"


def _cleanup():
    if WORK.exists():
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Remove-Item -Recurse -Force -LiteralPath '{WORK}'"],
                       capture_output=True)


def _ensure_clean():
    _cleanup()
    WORK.mkdir(parents=True, exist_ok=True)


def _copy_fixture(name):
    """Copy good-plan fixture to WORK/<name>/plan/ and return the plan path."""
    src = FIXTURE
    dst = WORK / name / "plan"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_pc():
    spec = importlib.util.spec_from_file_location("plan_check", ROOT / ".agents" / "scripts" / "plan-check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _lint(plan_dir):
    pc = _load_pc()
    plan = pc.Plan(Path(plan_dir), SCHEMAS)
    plan.load()
    return plan.run()


def _run_snapshot(repo, out, scopes=None, max_files=150):
    cmd = [sys.executable, str(ROOT / ".agents" / "scripts" / "repo-snapshot.py"),
           "--repo", str(repo), "--out", str(out), "--max-files", str(max_files)]
    if scopes:
        for s in scopes:
            cmd.extend(["--scope", s])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


# ──────────────────────────── Test 1: P0-1 snapshot cap fail-fast ────────────────────────────

def test_snapshot_cap_fail_fast():
    base = WORK / "test1" / "repo"
    out = WORK / "test1" / "snapshot.json"
    base.mkdir(parents=True, exist_ok=True)

    for i in range(11):
        f = base / f"mod{i}.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# mod {i}\n", encoding="utf-8")
    (base / "__init__.py").write_text("", encoding="utf-8")

    rc, stdout, stderr = _run_snapshot(base, out, max_files=10)
    assert rc != 0, f"Expected non-zero exit, got {rc}"
    assert not out.exists(), "Snapshot must NOT be produced when cap is exceeded"
    err = json.loads(stderr) if stderr else {}
    assert err.get("error") == "SNAPSHOT_SCOPE_TOO_LARGE", f"Wrong error: {err}"
    assert err.get("matched_files") == 12
    assert err.get("max_files") == 10
    print("  Test 1 PASS: snapshot cap fail-fast")


# ──────────────────────────── Test 2: P0-2 one-hop import outside scope ────────────────────────────

def test_one_hop_import_outside_scope():
    base = WORK / "test2" / "repo"
    out = WORK / "test2" / "snapshot.json"
    base.mkdir(parents=True, exist_ok=True)

    (base / "app" / "api").mkdir(parents=True, exist_ok=True)
    (base / "app" / "runtime").mkdir(parents=True, exist_ok=True)

    (base / "app/api/routes.py").write_text(
        "from app.runtime.state import RequestState\n\ndef handle():\n    return RequestState.get()\n",
        encoding="utf-8"
    )
    (base / "app/runtime/state.py").write_text(
        "class RequestState:\n    @staticmethod\n    def get(): ...\n",
        encoding="utf-8"
    )
    (base / "app/runtime/__init__.py").write_text("", encoding="utf-8")
    (base / "app/api/__init__.py").write_text("", encoding="utf-8")
    (base / "app/__init__.py").write_text("", encoding="utf-8")

    rc, _, _ = _run_snapshot(base, out, scopes=["app/api"])
    assert rc == 0, f"Snapshot failed: {rc}"
    snap = json.loads(out.read_text())
    paths = {f["path"] for f in snap["files"]}
    assert "app/api/routes.py" in paths, "seed file missing"
    assert "app/runtime/state.py" in paths, "one-hop import not in snapshot"
    expansions = snap.get("dependency_expansions", [])
    assert "app/runtime/state.py" in expansions, "not tracked as dependency_expansion"
    print("  Test 2 PASS: one-hop import outside scope")


# ──────────────────────────── Test 3: P0-3 auditor hard gates ────────────────────────────

def test_auditor_hard_gates():
    # Test 3a: grounding empty -> BLOCKER (grounding is required in schema;
    # empty dict passes schema but triggers AUDIT_NOT_GROUNDED in lint)
    plan1 = _copy_fixture("test3a")
    audit1 = _read_json(plan1 / "audit.json")
    audit1["grounding"] = {}
    _write_json(plan1 / "audit.json", audit1)
    findings = _lint(plan1)
    codes = {f["code"] for f in findings}
    assert "AUDIT_NOT_GROUNDED" in codes, f"Missing AUDIT_NOT_GROUNDED: {codes}"
    assert any(f["severity"] == "BLOCKER" for f in findings if f["code"] == "AUDIT_NOT_GROUNDED")

    # Test 3b: revision mismatch -> BLOCKER
    plan2 = _copy_fixture("test3b")
    audit2 = _read_json(plan2 / "audit.json")
    audit2["grounding"]["repo_revision"] = "WRONG_REVISION"
    _write_json(plan2 / "audit.json", audit2)
    findings = _lint(plan2)
    assert any(f["code"] == "AUDIT_SNAPSHOT_MISMATCH" and f["severity"] == "BLOCKER" for f in findings)

    # Test 3c: not isolated -> BLOCKER
    plan3 = _copy_fixture("test3c")
    audit3 = _read_json(plan3 / "audit.json")
    audit3["auditor"]["planner_conversation_isolated"] = False
    _write_json(plan3 / "audit.json", audit3)
    findings = _lint(plan3)
    assert any(f["code"] == "AUDIT_NOT_ISOLATED" and f["severity"] == "BLOCKER" for f in findings)

    print("  Test 3 PASS: auditor hard gates (grounding empty/mismatch/not-isolated -> BLOCKER)")


# ──────────────────────────── Test 4: P1-2 present + omitted conflict ────────────────────────────

def test_present_plus_omitted():
    plan = _copy_fixture("test4")
    integ = _read_json(plan / "integration-plan.json")
    # Add e2e_closure to omitted_kinds while it's already present as a primary task kind
    integ["omitted_kinds"].append({
        "kind": "e2e_closure", "reason": "already present",
        "evidence": ["see existing e2e task"]
    })
    _write_json(plan / "integration-plan.json", integ)
    findings = _lint(plan)
    invalid = [f for f in findings if f["code"] == "INVALID_INTEGRATION_MERGE"]
    assert any("e2e_closure" in f["detail"] for f in invalid), \
        f"No e2e_closure present+omitted conflict: {invalid}"
    print("  Test 4 PASS: present + omitted conflict -> INVALID_INTEGRATION_MERGE")


# ──────────────────────────── Test 5: P1-3 closure cannot be omission-only ────────────────────────────

def test_cannot_be_omission_only():
    plan = _copy_fixture("test5")
    integ = _read_json(plan / "integration-plan.json")
    # Replace e2e_closure task with contract_consistency (no real closure)
    for t in integ["integration_tasks"]:
        if t["kind"] == "e2e_closure":
            t["kind"] = "contract_consistency"
            t["merged_kinds"] = []  # remove final_acceptance merge
            break
    # Add e2e_closure and final_acceptance to omitted_kinds so they're "satisfied" by omission
    existing_omitted = {o["kind"] for o in integ["omitted_kinds"]}
    for kind in ("e2e_closure", "final_acceptance"):
        if kind not in existing_omitted:
            integ["omitted_kinds"].append({
                "kind": kind, "reason": "not needed for small plan",
                "evidence": ["plan is small"]
            })
    _write_json(plan / "integration-plan.json", integ)
    findings = _lint(plan)
    gates = [f for f in findings if f["code"] == "NO_INTEGRATION_GATE"]
    assert gates, f"Expected NO_INTEGRATION_GATE for omission-only closure: {findings}"
    assert gates[0]["severity"] == "BLOCKER"
    print("  Test 5 PASS: omission-only closure -> NO_INTEGRATION_GATE BLOCKER")


# ──────────────────────────── Test 6: P1-4 fresh-dir no longer auto-proves safe ────────────────────────────

def test_fresh_dir_no_auto_proof():
    plan = _copy_fixture("test6")
    # Modify a task to create a new file in a fresh directory
    candidates = _read_json(plan / "candidate-tasks.json")
    for t in candidates["tasks"]:
        if t["id"] == "T01":
            t["owned_paths"] = ["new/module/api_handler.py"]
            break

    # Remove seam coverage from the e2e_closure task so seams are NOT covered
    integ = _read_json(plan / "integration-plan.json")
    for it in integ["integration_tasks"]:
        if "seams" in it:
            it["seams"] = []  # remove seam coverage

    # Ensure seam_integration is omitted
    existing_omitted = {o["kind"] for o in integ["omitted_kinds"]}
    if "seam_integration" not in existing_omitted:
        integ["omitted_kinds"].append({
            "kind": "seam_integration",
            "reason": "new files land in a fresh directory - no existing wiring",
            "evidence": ["new/module/ is a new directory"]
        })

    _write_json(plan / "candidate-tasks.json", candidates)
    _write_json(plan / "integration-plan.json", integ)

    # Update snapshot to NOT contain the new file
    snap = _read_json(plan / "repo-context-snapshot.json")
    snap["files"] = [f for f in snap["files"]
                     if "new/module" not in f["path"]]
    _write_json(plan / "repo-context-snapshot.json", snap)

    findings = _lint(plan)
    hidden = [f for f in findings if f["code"] == "HIDDEN_INTEGRATION_WORK"]
    assert hidden, f"Expected HIDDEN_INTEGRATION_WORK even for fresh dir: {findings}"
    assert hidden[0]["severity"] == "BLOCKER"
    print("  Test 6 PASS: fresh directory no longer auto-proves seam omission safe")


# ──────────────────────────── Main ────────────────────────────

def main():
    _ensure_clean()
    try:
        print("Running targeted tests for 7 minimal fixes:")
        test_snapshot_cap_fail_fast()
        test_one_hop_import_outside_scope()
        test_auditor_hard_gates()
        test_present_plus_omitted()
        test_cannot_be_omission_only()
        test_fresh_dir_no_auto_proof()
        print("\nAll 6 targeted tests PASS.")
        return 0
    finally:
        _cleanup()


if __name__ == "__main__":
    sys.exit(main())
