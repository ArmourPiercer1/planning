"""Merge a baseline probe result into the parent v1.1 result's `baseline` field.

Usage: merge_baseline.py <probe> <run>
  e.g. merge_baseline.py P1 r1
Reads:  evals/probes/results/<probe>-v1.0-<run>.json  (baseline)
        evals/probes/results/<probe>-v1.1-<run>.json  (parent, updated in place)
The baseline result's own `baseline` field (always None) is dropped from the
embedded copy to avoid nested nulls.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

probe = sys.argv[1]
run = sys.argv[2]

base_path = RESULTS / f"{probe}-v1.0-{run}.json"
parent_path = RESULTS / f"{probe}-v1.1-{run}.json"

if not base_path.exists():
    print(f"baseline result missing: {base_path}")
    sys.exit(2)
if not parent_path.exists():
    print(f"parent result missing: {parent_path}")
    sys.exit(2)

base = json.loads(base_path.read_text(encoding="utf-8"))
parent = json.loads(parent_path.read_text(encoding="utf-8"))

embedded = {k: v for k, v in base.items() if k != "baseline"}
parent["baseline"] = embedded
parent_path.write_text(json.dumps(parent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

print(f"merged: {parent_path.name} <- baseline {probe} {base['version']} {base['run_id']} "
      f"(score {base['score']}, checks {sum(1 for c in base['checks'] if c['pass'])}/{len(base['checks'])})")
