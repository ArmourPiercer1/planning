#!/usr/bin/env python3
"""inline-frozen-contracts — migrate/re-inline Task Packages to @2 self-contained form.

Reads the plan's stage-contract.json, then for every tasks/<id>.json:
  * bumps the schema const planning/task-package@1 -> @2 (idempotent),
  * replaces each frozen_contracts entry with the FULL inlined spec plus
    source_ref and source_hash = sha256:<hex of the current spec>.

Run after editing stage-contract.json specs so packages never drift from the
contract (plan-check flags drift as STALE_CONTRACT_SNAPSHOT).

Usage:
    uv run --no-project python inline-frozen-contracts.py --plan-dir <dir> [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inline-frozen-contracts", description=__doc__)
    ap.add_argument("--plan-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    plan = Path(args.plan_dir)
    contract_path = plan / "stage-contract.json"
    if not contract_path.exists():
        print(json.dumps({"error": f"no stage-contract.json in {plan}"}))
        return 2
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    specs = {c["id"]: c for c in contract.get("shared_contracts", [])}

    tasks_dir = plan / "tasks"
    if not tasks_dir.is_dir():
        print(json.dumps({"error": f"no tasks/ dir in {plan}"}))
        return 2

    report = []
    for path in sorted(tasks_dir.glob("*.json")):
        pkg = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        if pkg.get("schema") == "planning/task-package@1":
            pkg["schema"] = "planning/task-package@2"
            changed = True
        new_fc = []
        for fc in pkg.get("frozen_contracts", []):
            cid = fc.get("contract_id")
            cur = specs.get(cid)
            if cur is None:
                new_fc.append(fc)
                report.append(f"{path.name}: {cid} NOT in stage-contract — left as-is")
                continue
            spec = cur["spec"]
            ref = fc.get("spec_ref") or fc.get("source_ref") or f"stage-contract.json#shared_contracts[{cid}]"
            new_fc.append({
                "contract_id": cid,
                "kind": cur.get("kind", "service"),
                "spec": spec,
                "source_ref": ref,
                "source_hash": "sha256:" + hashlib.sha256(spec.encode("utf-8")).hexdigest(),
            })
            if new_fc[-1] != fc:
                changed = True
        pkg["frozen_contracts"] = new_fc
        if changed and not args.dry_run:
            path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report.append(f"{path.name}: {'updated' if changed else 'unchanged'}")

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
