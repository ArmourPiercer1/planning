"""Aggregate run results into the summary report (markdown + json).

The report is deliberately structured so that no single metric can be read
in isolation: every metric table is paired with its gaming flags and with
the coverage legend (assessed / partial / not-measurable), and a dedicated
section lists which metrics must be read in groups.
"""

import json
from pathlib import Path

METRIC_ROWS = [
    ("contract_completeness", "Contract completeness", "higher"),
    ("acceptance_determinism", "Acceptance determinism", "higher"),
    ("context_locality", "Context locality (amplification proxy)", "lower"),
    ("ownership_collisions", "Hazardous ownership collisions", "lower"),
    ("dependency_precision", "Dependency precision (must-have hit rate)", "higher"),
    ("integration_explicitness", "Integration explicitness (case reqs met)", "higher"),
    ("leaf_boundedness", "Phase-shaped leaves", "lower"),
    ("recoverability", "Local recoverability", "higher"),
    ("scope_discipline", "Scope discipline", "higher"),
]


def _get_metric(res: dict, key: str):
    p = res.get("planning", {})
    if key == "contract_completeness":
        return p.get("contract_completeness")
    if key == "acceptance_determinism":
        return p.get("acceptance_determinism")
    if key == "context_locality":
        return p.get("context_locality", {}).get("amplification_proxy")
    if key == "ownership_collisions":
        return p.get("ownership_collisions", {}).get("hazardous")
    if key == "dependency_precision":
        mh = p.get("dependency_precision", {}).get("must_have", {})
        mnh = p.get("dependency_precision", {}).get("must_not_have", {})
        total = mh.get("total", 0) + mnh.get("total", 0)
        if total == 0:
            return None
        good = mh.get("hit", 0) + (mnh.get("total", 0) - mnh.get("violated", 0))
        return round(good / total, 4)
    if key == "integration_explicitness":
        return p.get("integration_explicitness", {}).get("case_requirements_met") \
            if p.get("integration_explicitness", {}).get("case_requirements_met") is not None \
            else p.get("integration_explicitness", {}).get("score")
    if key == "leaf_boundedness":
        return len(p.get("leaf_boundedness", {}).get("phase_shaped_leaves", []))
    if key == "recoverability":
        return p.get("recoverability", {}).get("score")
    if key == "scope_discipline":
        return p.get("scope_discipline", {}).get("score")
    return None


def _fmt(v, lower_is_better):
    if v is None:
        return "n/m"
    if isinstance(v, float):
        s = f"{v:.2f}"
    else:
        s = str(v)
    return s


def aggregate(results: list[dict]) -> dict:
    """results: list of run-result dicts (one per run)."""
    by_variant: dict[str, list[dict]] = {}
    for r in results:
        by_variant.setdefault(r["planner_variant"], []).append(r)

    per_variant = {}
    for variant, rs in by_variant.items():
        rows = []
        for key, label, direction in METRIC_ROWS:
            vals = [v for v in (_get_metric(r, key) for r in rs) if v is not None]
            if vals:
                mean = sum(vals) / len(vals)
                worst = max(vals) if direction == "lower" else min(vals)
                row = {"metric": label, "direction": direction,
                       "mean": round(mean, 4), "min": round(min(vals), 4),
                       "max": round(max(vals), 4), "measured_runs": len(vals),
                       "total_runs": len(rs), "worst_run_case": None}
                if direction == "lower":
                    row["worst_run_case"] = max(rs, key=lambda r: (_get_metric(r, key) is not None, _get_metric(r, key) or 0))["case_id"]
                else:
                    row["worst_run_case"] = min((r for r in rs if _get_metric(r, key) is not None),
                                                key=lambda r: _get_metric(r, key), default={"case_id": None})["case_id"]
            else:
                row = {"metric": label, "direction": direction, "mean": None, "min": None,
                       "max": None, "measured_runs": 0, "total_runs": len(rs), "worst_run_case": None}
            rows.append(row)
        e_vec = {}
        for dim in ("success", "wall_time", "tokens", "context_read", "rework",
                    "integration_defects", "scope_creep", "replans", "compactions",
                    "local_recoverability"):
            vals = [r["e_vector"].get(dim) for r in rs if r["e_vector"].get(dim) is not None]
            e_vec[dim] = {"mean": (sum(vals) / len(vals)) if vals else None, "n": len(vals)}
        flags = {}
        for r in rs:
            for f in r.get("planning", {}).get("gaming_flags", []):
                flags.setdefault(f["code"], []).append(f"{r['case_id']}: {f.get('detail', '')}")
        judge = []
        for r in rs:
            for j in r.get("planning", {}).get("judge_pending", []):
                judge.append(f"{r['case_id']}/{r['planner_variant']}: {j['dimension']} — {j['reason']}")
        per_variant[variant] = {"metrics": rows, "e_vector": e_vec,
                                "gaming_flags": flags, "judge_pending": judge,
                                "runs": len(rs)}
    return per_variant


REPORT_NOTES = """
## How to read this report (do not read single metrics)

- **Context locality (amplification proxy) ↓ can be gamed** by omitting required
  context. Read it TOGETHER with contract completeness and dependency precision:
  a plan with low context but missing must-have dependencies is not "local",
  it is starved (see gaming flag G3_CONTEXT_STARVATION).
- **Task count ↓ can be gamed** by one giant task. Read it TOGETHER with
  leaf boundedness (phase-shaped leaves) and integration explicitness.
- **Integration explicitness ↑ can be gamed** by one mega integration task
  owning all fixes (flag G5_MEGA_INTEGRATION).
- **Recoverability ↑ can be gamed** by blanket checkpoint_required on trivial
  tasks; V1 records the structure, the execution smoke validates the payoff.
- **Scope discipline ↑ must be checked against the case traps**, not the
  plan's self-description: the scorer checks repo files, not prose.
- **Per-case matrix legend**: `lint`/`LINT-FAIL` = deterministic gate exit;
  `mnh✓` = no forbidden edge present, `mnh✗ v/t` = v of t forbidden edges
  present (a violation); `CREEP×n` = n scope-creep items found in the plan;
  `count✓`/`count✗` = task count inside/outside the case's acceptable range;
  `—` = that variant was not run for this case.
- **Coverage legend**: `assessed` = fully programmatic; `partial` = `partial` =
  keyword/structural proxy (baselines); `n/m` = not measurable from the
  artifact form — a `n/m` cell is NOT a zero.
- **E vector is the primary result** (bootstrap §2.4): the composite tables
  above are conveniences; per-run E vectors are in the JSON report.
"""


def render_markdown(run_id: str, results: list[dict], agg: dict) -> str:
    lines = [f"# Eval report — run `{run_id}`", ""]
    lines.append(f"runs: {len(results)} | variants: {', '.join(sorted(agg))}")
    lines.append("")
    for variant, data in sorted(agg.items()):
        lines.append(f"## Variant: `{variant}` ({data['runs']} runs)")
        lines.append("")
        lines.append("| Metric | Direction | Mean | Min | Max | Measured | Worst run |")
        lines.append("|---|---|---:|---:|---:|---|---|")
        for row in data["metrics"]:
            lines.append(
                f"| {row['metric']} | {row['direction']} | "
                f"{_fmt(row['mean'], row['direction'])} | {_fmt(row['min'], row['direction'])} | "
                f"{_fmt(row['max'], row['direction'])} | {row['measured_runs']}/{row['total_runs']} | "
                f"{row['worst_run_case'] or '—'} |"
            )
        lines.append("")
        lines.append("### E vector (planning-phase proxies where noted)")
        lines.append("")
        lines.append("| Dimension | Mean | n |")
        lines.append("|---|---:|---:|")
        for dim, v in data["e_vector"].items():
            mean = v["mean"]
            lines.append(f"| {dim} | {'n/a' if mean is None else (f'{mean:.3f}' if isinstance(mean, float) else mean)} | {v['n']} |")
        lines.append("")
        if data["gaming_flags"]:
            lines.append("### Gaming flags")
            lines.append("")
            for code, details in sorted(data["gaming_flags"].items()):
                lines.append(f"- **{code}**")
                for d in details:
                    lines.append(f"  - {d}")
            lines.append("")
        if data["judge_pending"]:
            lines.append("### Judge-pending (not automated in V1)")
            lines.append("")
            for j in data["judge_pending"]:
                lines.append(f"- {j}")
            lines.append("")

    # per-case constraint matrix
    cases = sorted({r["case_id"] for r in results})
    variants = sorted(agg)
    lines.append("## Per-case matrix (key constraints)")
    lines.append("")
    lines.append("| Case | " + " | ".join(variants) + " |")
    lines.append("|---|" + "---|" * len(variants))
    for c in cases:
        cells = []
        for v in variants:
            r = next((x for x in results if x["case_id"] == c and x["planner_variant"] == v), None)
            if not r:
                cells.append("—")
                continue
            p = r.get("planning", {})
            parts = []
            if p.get("structural_validity", {}).get("lint_exit") is not None:
                parts.append("lint" if p["structural_validity"]["lint_exit"] == 0 else "LINT-FAIL")
            mh = p.get("dependency_precision", {}).get("must_not_have", {})
            if mh.get("total"):
                v = mh.get("violated", 0)
                parts.append("mnh✓" if v == 0 else f"mnh✗ {v}/{mh['total']}")
            sd = p.get("scope_discipline", {})
            if sd.get("creep_items_planned"):
                parts.append(f"CREEP×{len(sd['creep_items_planned'])}")
            tc = p.get("task_count", {})
            if tc.get("in_range") is not None:
                parts.append("count✓" if tc["in_range"] else "count✗")
            cells.append(" ".join(parts) or "n/m")
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(REPORT_NOTES)
    return "\n".join(lines)


def write_report(run_id: str, results: list[dict], out_dir: Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    agg = aggregate(results)
    md_path = out_dir / f"{run_id}-report.md"
    json_path = out_dir / f"{run_id}-report.json"
    md_path.write_text(render_markdown(run_id, results, agg), encoding="utf-8")
    payload = {
        "run_id": run_id,
        "per_variant": agg,
        "runs": [
            {k: r.get(k) for k in ("run_id", "case_id", "planner_variant", "model", "phase", "e_vector")}
            for r in results
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return md_path, json_path
