"""Artifact tests: every shared schema and every example/fixture artifact
must validate against the mini-validator, and the example plan must lint
clean. This is the test proving the plan artifacts are machine-consumable
(the interface the evals bootstrap depends on)."""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PC = ROOT / ".agents" / "scripts" / "plan-check.py"
SCHEMAS = ROOT / ".agents" / "schemas" / "planning"
EXAMPLE = ROOT / "examples" / "long-task-planning"


def _load_pc():
    spec = importlib.util.spec_from_file_location("plan_check", PC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pc = _load_pc()


def _lint(plan_dir):
    plan = pc.Plan(Path(plan_dir), SCHEMAS)
    plan.load()
    return plan, plan.run()


def run():
    problems = []

    # 1. schemas: parse + shape
    schema_files = sorted(SCHEMAS.glob("*.schema.json"))
    if len(schema_files) < 10:
        problems.append(f"expected >= 10 schemas in {SCHEMAS}, found {len(schema_files)}")
    for sf in schema_files:
        try:
            schema = json.loads(sf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{sf.name}: not valid JSON — {e}")
            continue
        if not isinstance(schema, dict) or "type" not in schema:
            problems.append(f"{sf.name}: schema missing top-level 'type'")
        if not str(schema.get("$id", "")).startswith("planning/"):
            problems.append(f"{sf.name}: $id must be 'planning/<kind>@N'")

    # 2. every JSON artifact under the example plan validates
    example_files = sorted(EXAMPLE.rglob("*.json"))
    if len(example_files) < 10:
        problems.append(f"expected >= 10 example artifacts, found {len(example_files)}")
    for f in example_files:
        res = pc.validate_file(f, SCHEMAS)
        if not res["ok"]:
            problems.append(f"example {f.relative_to(EXAMPLE)}: schema-invalid — {res['errors'][:2]}")

    # 3. example plan lints clean (zero findings at any severity)
    plan, findings = _lint(EXAMPLE)
    for f in findings:
        problems.append(f"example plan lint: {f['severity']} {f['code']} {f['detail'][:80]}")

    # 4. good-plan fixture is fully clean
    good = HERE / "fixtures" / "good-plan"
    gplan, gfindings = _lint(good)
    for f in gfindings:
        problems.append(f"good-plan fixture lint (expected clean): {f['severity']} {f['code']}")

    # 5. audit.json in the example is a PASS verdict (the example is the
    #    canonical end state)
    audit = json.loads((EXAMPLE / "audit.json").read_text(encoding="utf-8"))
    if audit.get("verdict") != "PASS":
        problems.append(f"example audit.json verdict is {audit.get('verdict')!r}, expected PASS")

    for p in problems:
        print(f"FAIL: {p}")
    if not problems:
        print(f"PASS: {len(schema_files)} schemas, {len(example_files)} example artifacts, "
              f"example lint clean, good-plan fixture clean")
    return len(problems)


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
