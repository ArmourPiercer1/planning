"""Static Plan Quality scorer (Layer 1).

Scores a produced plan against one case's machine-readable expected
constraints. Two input forms:
  - candidate/ablation plans: the planning skill's JSON artifacts
    (stage-contract.json, candidate-tasks.json, dag.json, ...)
  - baseline plans: markdown prose (free-form or checklist)

Design rules (evals bootstrap §2):
  - constraint satisfaction, not text equality;
  - everything programmatic here; dimensions that cannot be decided
    programmatically are returned as null + a judge_pending entry, never a
    guessed number;
  - every score carries details/evidence so the report is auditable;
  - gaming guards run over the metric set, never over a single metric.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # planning/
PC_PATH = ROOT / ".agents" / "scripts" / "plan-check.py"
SCHEMAS_PLANNING = ROOT / ".agents" / "schemas" / "planning"
SCHEMAS_EVALS = HERE.parent / "schemas"

sys.path.insert(0, str(HERE))
import prose_parser  # noqa: E402


def _load_pc():
    spec = importlib.util.spec_from_file_location("plan_check", PC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pc = _load_pc()


def validate_json_against(instance: dict, schema_file: Path) -> list[str]:
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    return pc.validate_against(instance, schema)


# ---------------------------------------------------------------------------
# Anchor mapping
# ---------------------------------------------------------------------------

def _declared_path(p: str) -> str:
    """'app/x.py (new)' -> 'app/x.py'; tolerate ./ prefix."""
    return p.split(" ")[0].strip().lstrip("./")


def _overlaps(declared: str, anchor_file: str) -> bool:
    d, a = _declared_path(declared), anchor_file.strip()
    if d == a:
        return True
    d, a = d.rstrip("/"), a.rstrip("/")
    return d.startswith(a + "/") or a.startswith(d + "/")


def _task_context_files(task: dict) -> list[str]:
    rc = task.get("required_context", {})
    files = list(rc.get("files", [])) if isinstance(rc, dict) else []
    return files


def map_task_anchors(case: dict, task: dict, use_context: bool = False) -> set[str]:
    """Anchor ids a task touches, via owned_paths (primary) and optionally
    required_context (secondary evidence)."""
    files = list(task.get("owned_paths", []))
    if use_context:
        files += _task_context_files(task)
    ids = set()
    for a in case["anchors"]:
        for f in files:
            if any(_overlaps(f, af) for af in a["files"]):
                ids.add(a["id"])
                break
    return ids


def _anchor_text(case: dict, anchor_id: str) -> str:
    for a in case["anchors"]:
        if a["id"] == anchor_id:
            return a.get("description", "") + " " + " ".join(a["files"])
    return ""


def _text_mentions_anchor(text: str, case: dict, anchor_id: str) -> bool:
    """Weak match: any anchor file (basename or path) in the text."""
    low = text.lower()
    for a in case["anchors"]:
        if a["id"] == anchor_id:
            for f in a["files"]:
                if f.lower() in low or f.split("/")[-1].lower() in low:
                    return True
    return False


# ---------------------------------------------------------------------------
# Candidate (structured) plan scoring
# ---------------------------------------------------------------------------

def _graph(ids: list[str], edges: list[dict]):
    adj = {t: [] for t in ids}
    for e in edges:
        if e["from"] in adj and e["to"] in adj:
            adj[e["from"]].append(e["to"])
    return adj


def _reachable_from(adj: dict, start: str) -> set[str]:
    seen, stack = set(), [start]
    while stack:
        cur = stack.pop()
        for nxt in adj.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def score_candidate_plan(case: dict, plan_dir: Path) -> dict:
    plan_dir = Path(plan_dir)
    plan = pc.Plan(plan_dir, SCHEMAS_PLANNING)
    plan.load()
    findings = plan.run()
    counts = {sev: sum(1 for f in findings if f["severity"] == sev) for sev in ("BLOCKER", "MAJOR", "MINOR")}
    lint_exit = 1 if counts["BLOCKER"] else 0
    audit_verdict = plan.audit.get("verdict") if plan.audit else None
    audit_rounds = plan.audit.get("revision_round") if plan.audit else None
    candidates = (plan.candidates or {}).get("tasks", [])
    int_tasks = (plan.integration or {}).get("integration_tasks", [])
    int_seams = (plan.integration or {}).get("seams", [])
    e2e_gates = (plan.integration or {}).get("e2e_gates", [])
    edges = (plan.dag or {}).get("edges", [])
    contract = plan.contract or {}
    packages = plan.packages
    all_ids = plan.task_ids()
    adj = _graph(all_ids, edges)

    out: dict = {"produced": bool(candidates), "variant_kind": "structured", "findings": findings}
    out["structural_validity"] = {
        "lint_exit": lint_exit,
        # lowercase keys: the run-result schema (planning-evals/run-result@1)
        # is the wire contract for these counts
        "findings": {k.lower(): v for k, v in counts.items()},
        "audit_verdict": audit_verdict,
        "audit_rounds": audit_rounds,
    }

    # task -> anchors (owned paths primary)
    tanchors = {t["id"]: map_task_anchors(case, t) for t in candidates}
    for it in int_tasks:
        tanchors.setdefault(it["task_id"], map_task_anchors(case, it))
        pkg = packages.get(it["task_id"], {})
        tanchors[it["task_id"]] |= map_task_anchors(case, pkg, use_context=True) if pkg else set()

    def tasks_covering(anchor_id: str) -> list[str]:
        return [tid for tid, a in tanchors.items() if anchor_id in a]

    expected = case["expected"]
    coverage: dict[str, str] = {}
    judge: list[dict] = []

    # ---- 3.1 contract completeness -------------------------------------
    cc_details = []
    checks = [
        ("objective", bool((contract.get("objective") or "").strip())
         and pc.OUTCOME_VERBS.search(contract.get("objective", "")), "objective present with an outcome verb"),
        ("in_scope", bool(contract.get("in_scope")), "in_scope non-empty"),
        ("out_of_scope", any((o.get("reason") or "").strip() for o in contract.get("out_of_scope", [])),
         "out_of_scope non-empty with reasons"),
        ("frozen_assumptions", bool(contract.get("frozen_assumptions")), "frozen assumptions listed"),
        ("frozen_contracts", bool(contract.get("shared_contracts")), "shared/frozen contracts defined"),
        ("acceptance", bool(contract.get("acceptance")), "acceptance criteria present"),
        ("integration_seams", bool(contract.get("integration_seams")), "integration seams named"),
        ("constraints", bool(contract.get("constraints")), "constraints present"),
        ("allowed_replan", bool(contract.get("allowed_replan")), "allowed replan actions defined"),
    ]
    out["contract_completeness"] = round(sum(1 for _, ok, _ in checks if ok) / len(checks), 4)
    cc_details = [{"field": n, "ok": bool(ok), "check": d} for n, ok, d in checks]
    coverage["contract_completeness"] = "assessed"

    # ---- 3.2 acceptance determinism ------------------------------------
    acc_items = []
    for a in contract.get("acceptance", []):
        for field in ("description", "positive_case", "negative_case", "failure_behavior", "evidence"):
            v = a.get(field)
            if isinstance(v, str) and v.strip():
                acc_items.append(v)
    for tid, pkg in packages.items():
        for at in pkg.get("acceptance_tests", []):
            acc_items.append(at.get("description", ""))
        for fc in pkg.get("failure_cases", []):
            acc_items.append(fc.get("expected_behavior", ""))
    det = 0
    for v in acc_items:
        vague_hit = [w for w in pc.VAGUE_EN if re.search(w, v, re.IGNORECASE)] \
            or [w for w in pc.VAGUE_ZH if w in v]
        has_marker = bool(pc.EVIDENCE_MARKERS.search(v))
        if not vague_hit and has_marker:
            det += 1
    out["acceptance_determinism"] = round(det / len(acc_items), 4) if acc_items else None
    coverage["acceptance_determinism"] = "assessed" if acc_items else "not-measurable"
    if not acc_items:
        judge.append({"dimension": "acceptance_determinism", "reason": "no acceptance text found to scan"})

    # ---- 3.3 context locality ------------------------------------------
    per_task = []
    amplifs = []
    max_files = 0
    bare_dirs = []
    for t in candidates:
        files = [_declared_path(f) for f in _task_context_files(t)]
        owned = [ _declared_path(f) for f in t.get("owned_paths", [])]
        bare = [f for f in files if f in ("", ".", "/", "app", "src") or (f.endswith("/") and "." not in f.split("/")[-1])]
        bare_dirs += [f"{t['id']}:{b}" for b in bare]
        cross = sum(1 for f in files
                    if any(_overlaps(f, af) for a in case["anchors"] for af in a["files"]
                           if a["id"] not in tanchors[t["id"]]))
        amplif = len(set(files)) / max(1, len(owned))
        amplifs.append(amplif)
        max_files = max(max_files, len(set(files)))
        per_task.append({
            "task": t["id"], "context_files": len(set(files)), "owned_files": len(owned),
            "amplification_proxy": round(amplif, 3), "cross_anchor_reads": cross, "bare_directories": bare,
        })
    out["context_locality"] = {
        "amplification_proxy": round(sum(amplifs) / len(amplifs), 3) if amplifs else None,
        "per_task": per_task,
        "max_context_files": max_files,
        "bare_directories": bare_dirs,
    }
    coverage["context_locality"] = "assessed"

    # ---- 3.4 ownership collisions --------------------------------------
    reach = {t: _reachable_from(adj, t) for t in all_ids}
    collisions = {"benign": 0, "serialized": 0, "hazardous": 0, "details": []}
    cand_ids = [t["id"] for t in candidates]
    cand_owned = {t["id"]: [_declared_path(f) for f in t.get("owned_paths", [])] for t in candidates}
    for i in range(len(cand_ids)):
        for j in range(i + 1, len(cand_ids)):
            a, b = cand_ids[i], cand_ids[j]
            shared = [f for f in cand_owned[a] if f in cand_owned[b]]
            if not shared:
                continue
            ordered = b in reach.get(a, set()) or a in reach.get(b, set())
            if not ordered:
                kind = "hazardous"
            else:
                kind = "serialized"
            collisions[kind] += 1
            collisions["details"].append({"tasks": [a, b], "shared_paths": shared, "ordered": ordered, "kind": kind})
    out["ownership_collisions"] = collisions
    coverage["ownership_collisions"] = "assessed"

    # ---- 3.5 dependency precision --------------------------------------
    def edge_anchors_hit(frm, to):
        for e in edges:
            if e["from"] in tanchors and e["to"] in tanchors:
                if frm in tanchors[e["from"]] and to in tanchors[e["to"]]:
                    return e
        return None

    def internalized(frm, to):
        return any(frm in s and to in s for s in tanchors.values())

    mh_details = []
    mh_hit = 0
    for spec in expected.get("must_have_edges", []):
        e = edge_anchors_hit(spec["from_anchor"], spec["to_anchor"])
        ok = e is not None or internalized(spec["from_anchor"], spec["to_anchor"])
        mh_hit += int(ok)
        mh_details.append({
            "from": spec["from_anchor"], "to": spec["to_anchor"], "hit": bool(ok),
            "via": (f"edge {e['from']}->{e['to']}" if e else "internalized in one task" if ok else None),
        })
    mnh_details = []
    mnh_violated = 0
    for spec in expected.get("must_not_have_edges", []):
        a, b = spec["from_anchor"], spec["to_anchor"]
        hit = edge_anchors_hit(a, b) or edge_anchors_hit(b, a)
        violated = hit is not None and not internalized(a, b)
        mnh_violated += int(violated)
        mnh_details.append({"from": a, "to": b, "violated": bool(violated),
                            "reason": spec["reason"],
                            "via": (f"edge {hit['from']}->{hit['to']}" if hit else None)})
    unknown_edges = sum(1 for f in findings if f["code"] == "DAG_UNKNOWN_TASK")
    edges_without_reason = sum(1 for e in edges
                               if not (e.get("reason") or "").strip() or not (e.get("type") or "").strip())
    out["dependency_precision"] = {
        "must_have": {"hit": mh_hit, "total": len(expected.get("must_have_edges", [])), "details": mh_details},
        "must_not_have": {"violated": mnh_violated, "total": len(expected.get("must_not_have_edges", [])), "details": mnh_details},
        "cycles": sum(1 for f in findings if f["code"] == "DAG_CYCLE"),
        "edges_without_reason": edges_without_reason,
        "unknown_task_edges": unknown_edges,
    }
    coverage["dependency_precision"] = "assessed"

    # parallelizable groups (no ordering between the group's tasks)
    # Membership is restricted to LEAF (candidate) tasks: integration/
    # verification tasks are downstream by design and read the anchors' files
    # via required_context, which would otherwise make every legitimate
    # downstream gate look like fake serialization of the group.
    par_ok = []
    for grp in expected.get("parallelizable_groups", []):
        members = set()
        for aid in grp["anchor_ids"]:
            members |= set(tasks_covering(aid))
        members = [m for m in members if m in cand_ids]
        ok = True
        bad = None
        for x in members:
            for y in members:
                if x != y and (y in reach.get(x, set())):
                    ok = False
                    bad = f"{x}->{y}"
        par_ok.append({"anchors": grp["anchor_ids"], "tasks": members, "ok": ok, "violated_by": bad})
    out["parallelizable_groups"] = par_ok

    # forbidden parallel pairs
    fpp_details = []
    for pp in expected.get("forbidden_parallel_pairs", []):
        a, b = pp["anchor_ids"]
        ta, tb = tasks_covering(a), tasks_covering(b)
        shared = _declared_path(pp["shared_path"])
        hazardous = False
        evidence = None
        for x in ta:
            for y in tb:
                if x == y:
                    continue  # internalized
                if y in reach.get(x, set()) or x in reach.get(y, set()):
                    continue  # serialized resolves it
                # hazard = both tasks OWN the shared path (a read in
                # required_context is legitimate shared context, not a collision)
                x_touches = any(_overlaps(f, shared) for f in cand_owned.get(x, []))
                y_touches = any(_overlaps(f, shared) for f in cand_owned.get(y, []))
                if x_touches and y_touches:
                    hazardous = True
                    evidence = f"unordered pair {x},{y} both own {shared}"
        fpp_details.append({"anchors": [a, b], "shared_path": pp["shared_path"],
                            "hazardous": hazardous, "evidence": evidence,
                            "note": pp.get("note")})
    out["forbidden_parallel_pairs"] = fpp_details

    # ---- 3.7 integration explicitness ----------------------------------
    by_kind = {"contract_consistency": 0, "seam_integration": 0, "e2e_closure": 0, "final_acceptance": 0}
    for it in int_tasks:
        if it.get("kind") in by_kind:
            by_kind[it["kind"]] += 1
    failure_gates = 0
    gate_text_all = " ".join(str(g.get("scenario", "")) for g in e2e_gates).lower()
    for g in e2e_gates:
        s = str(g.get("scenario", "")).lower()
        if re.search(r"fail|error|crash|exhaust|retry|missing|invalid|corrupt|conflict|timeout|reject", s):
            failure_gates += 1
    fixes_owned = sum(len(it.get("owns_fixes_for", [])) for it in int_tasks)

    def it_anchors(it: dict) -> set[str]:
        s = set(tanchors.get(it["task_id"], set()))
        for t in it.get("owns_fixes_for", []):
            s |= tanchors.get(t, set())
        return s

    gate_reqs = expected.get("required_integration_gates", [])
    gate_ok = 0
    gate_details = []
    for gr in gate_reqs:
        kind_ok = by_kind.get(gr["kind"], 0) > 0
        anchor_ok = (all(aid in it_anchors(it) for aid in gr["anchor_ids"])
                     for it in int_tasks)
        anchor_ok = any(anchor_ok) if gr.get("anchor_ids") else True
        markers = gr.get("failure_path_markers", [])
        marker_ok = True
        missing_markers = []
        for mk in markers:
            if not any(k.lower() in gate_text_all for k in mk["keywords"]):
                marker_ok = False
                missing_markers.append(mk["path"])
        ok = kind_ok and anchor_ok and marker_ok
        gate_ok += int(ok)
        gate_details.append({"kind": gr["kind"], "anchors": gr.get("anchor_ids", []),
                             "ok": ok, "missing_failure_markers": missing_markers,
                             "kind_present": kind_ok, "anchors_covered": anchor_ok})
    out["integration_explicitness"] = {
        "score": round(gate_ok / len(gate_reqs), 4) if gate_reqs else (1.0 if int_tasks else 0.0),
        "by_kind": by_kind,
        "e2e_gates": len(e2e_gates),
        "failure_gates": failure_gates,
        "fixes_owned": fixes_owned,
        "case_requirements_met": round(gate_ok / len(gate_reqs), 4) if gate_reqs else None,
        "gate_details": gate_details,
    }
    coverage["integration_explicitness"] = "assessed"

    # ---- 3.6 leaf boundedness ------------------------------------------
    cap = expected.get("max_anchors_per_task")
    phase_leaves = []
    over_cap = 0
    max_obs = 0
    for t in candidates:
        n = len(tanchors[t["id"]])
        max_obs = max(max_obs, n)
        files = len(_task_context_files(t))
        if (cap and n > cap) or files > 12 or n >= 4:
            phase_leaves.append(t["id"])
        if cap and n > cap:
            over_cap += 1
    out["leaf_boundedness"] = {
        "phase_shaped_leaves": phase_leaves,
        "max_anchors_per_task_observed": max_obs,
        "over_anchor_cap": over_cap,
    }
    coverage["leaf_boundedness"] = "assessed"

    # ---- 3.8 recoverability --------------------------------------------
    rec = expected.get("recoverable_tasks", [])
    rec_per = []
    rec_ok = 0
    for aid in rec:
        ts = [t for t in tasks_covering(aid) if t in cand_ids]
        ok = False
        why = "no task covers the anchor"
        for tid in ts:
            pkg = packages.get(tid, {})
            chk = (pkg.get("handoff", {}) or {}).get("checkpoint_required")
            if chk is True:
                ok = True
                why = f"{tid} checkpoint_required"
        rec_ok += int(ok)
        rec_per.append({"anchor": aid, "ok": ok, "why": why})
    out["recoverability"] = {
        "score": round(rec_ok / len(rec), 4) if rec else None,
        "per_anchor": rec_per,
    }
    coverage["recoverability"] = "assessed" if rec else "not-measurable"

    # ---- 3.9 scope discipline ------------------------------------------
    creep = []
    named = []
    mne = expected.get("must_not_expand_scope", [])
    oos_text = " ".join(str(o.get("item", "")) + " " + str(o.get("reason", ""))
                        for o in contract.get("out_of_scope", []))
    all_planned_text = json.dumps(candidates) + json.dumps(int_tasks) + json.dumps(contract.get("in_scope", []))
    for p in mne:
        base = p.split("/")[-1]
        planned = (p.lower() in all_planned_text.lower()) or (base.lower() in all_planned_text.lower())
        if planned:
            creep.append(p)
        if p.lower() in oos_text.lower() or base.lower() in oos_text.lower():
            named.append(p)
    out["scope_discipline"] = {
        "creep_items_planned": creep,
        "out_of_scope_named": named,
        "score": round(1 - len(creep) / len(mne), 4) if mne else 1.0,
    }
    coverage["scope_discipline"] = "assessed"

    # must_not_own
    mno = expected.get("must_not_own", [])
    own_violations = []
    for p in mno:
        for t in candidates:
            if any(_overlaps(f, p) for f in t.get("owned_paths", [])):
                own_violations.append(f"{t['id']} owns {p}")
    out["must_not_own_violations"] = own_violations

    # ---- task count + clusters + replan + contract-change path ----------
    rng = expected.get("acceptable_task_count_range")
    actual = len(candidates)
    out["task_count"] = {
        "actual": actual,
        "range": rng,
        "in_range": (rng[0] <= actual <= rng[1]) if rng else None,
    }
    cluster_details = []
    for cl in expected.get("context_clusters", []):
        a, mode = cl["anchor_ids"], cl["mode"]
        if mode == "merge":
            ok = any(all(x in s for x in a) for s in tanchors.values())
        else:
            ok = not any(len(s & set(a)) >= 2 for s in tanchors.values())
        cluster_details.append({"anchors": a, "mode": mode, "ok": ok})
    out["context_clusters"] = cluster_details

    allowed = set(contract.get("allowed_replan", []))
    req_actions = expected.get("required_replan_actions", [])
    out["required_replan_actions"] = {
        "required": req_actions,
        "allowed": sorted(allowed),
        "missing": [a for a in req_actions if a not in allowed],
    }

    ccr = expected.get("required_contract_change_path")
    if ccr:
        blob = json.dumps(contract) + " " + " ".join(json.dumps(p) for p in packages.values()) + " " + json.dumps(plan.integration or {})
        anchor_mentioned = any(_text_mentions_anchor(blob, case, a) for a in ccr["anchor_ids"])
        marker_hit = [m for m in ccr["marker_terms"] if m.lower() in blob.lower()]
        out["contract_change_path"] = {
            "ok": anchor_mentioned and bool(marker_hit),
            "anchor_mentioned": anchor_mentioned,
            "marker_hit": marker_hit,
            "note": ccr.get("note"),
        }
        coverage["contract_change_path"] = "assessed"
        if anchor_mentioned and not marker_hit:
            judge.append({"dimension": "contract_change_path",
                          "reason": "interface mentioned but no formal change-request/blocker mechanism found in plan text"})

    # ---- gaming guards (§13) -------------------------------------------
    flags = []
    if rng and actual > rng[1]:
        flags.append({"code": "G1_OVER_FRAGMENTED", "detail": f"{actual} tasks > range max {rng[1]}"})
    if expected.get("parallelizable_groups"):
        if not edges:
            flags.append({"code": "G2_ALL_SERIAL",
                          "detail": "case has parallelizable anchors but the plan declares no edges at all"})
        elif par_ok and not any(p["ok"] for p in par_ok):
            flags.append({"code": "G2_ALL_SERIAL",
                          "detail": "every parallelizable anchor group is ordered by an edge"})
    if candidates:
        zero_ctx = sum(1 for t in candidates if not _task_context_files(t))
        if zero_ctx / len(candidates) > 0.3:
            flags.append({"code": "G3_CONTEXT_STARVATION", "detail": f"{zero_ctx}/{len(candidates)} tasks declare no required context"})
    mega = [it["task_id"] for it in int_tasks if len(it.get("owns_fixes_for", [])) > max(1, len(candidates) * 0.5)]
    if mega and len(int_tasks) == 1:
        flags.append({"code": "G5_MEGA_INTEGRATION", "detail": f"single integration task owns fixes for >50% of leaves: {mega}"})
    blocker_text_hits = sum(1 for p in packages.values()
                            for b in (p.get("failure_cases", []) or [])
                            if "blocker" in json.dumps(b).lower())
    if len(candidates) and blocker_text_hits > max(1, len(candidates) * 0.5):
        flags.append({"code": "G6_BLOCKER_ESCAPE", "detail": f"{blocker_text_hits} blocker-laden failure cases across {len(candidates)} tasks"})
    out["gaming_flags"] = flags

    out["judge_pending"] = judge
    out["metric_coverage"] = coverage
    return out


# ---------------------------------------------------------------------------
# Baseline (prose) plan scoring
# ---------------------------------------------------------------------------

def score_prose_plan(case: dict, plan_text: str, repo_files: list[str]) -> dict:
    parsed = prose_parser.parse_plan_md(plan_text, repo_files)
    expected = case["expected"]
    out: dict = {"produced": parsed["word_count"] > 80, "variant_kind": "prose", "parse": parsed}
    out["structural_validity"] = {
        "lint_exit": None, "findings": {"blocker": 0, "major": 0, "minor": 0},
        "audit_verdict": None, "audit_rounds": None,
        "note": "n/a for prose plans (no schema artifacts)",
    }
    coverage = {}
    judge = []

    # contract completeness via section/keyword presence
    groups = {
        "objective": r"objective|goal|the task|task is|we need",
        "in_scope": r"in.?scope|scope of (this|the work)|deliverables",
        "out_of_scope": r"out.?of.?scope|non.?goals?|not (doing|including|in scope)|excluded|beyond",
        "frozen_assumptions": r"assumption|assume",
        "frozen_contracts": r"architecture|interface|contract|schema|api shape|shared (interface|schema)",
        "acceptance": r"acceptance|definition of done|success criteria|verification|tests? (pass|to verify)",
        "integration_seams": r"integration|seam|end.to.end|wiring|boundary between",
        "constraints": r"constraint|limitation|must not|budget|do not touch",
        "allowed_replan": r"replan|fallback|if (this|it) (fails|goes wrong)|contingency|pivot",
    }
    low = plan_text.lower()
    hits = [name for name, pat in groups.items() if re.search(pat, low)]
    out["contract_completeness"] = round(len(hits) / len(groups), 4)
    out["contract_completeness_detail"] = hits
    coverage["contract_completeness"] = "partial"

    # acceptance determinism
    acc = parsed["acceptance_text"]
    if acc.strip():
        vague_hits = [w for w in pc.VAGUE_EN if re.search(w, acc, re.IGNORECASE)]
        has_test = bool(re.search(r"test|verify|assert|check that", acc, re.IGNORECASE))
        out["acceptance_determinism"] = 1.0 if (not vague_hits and has_test) else (0.5 if has_test else 0.0)
        coverage["acceptance_determinism"] = "partial"
    else:
        out["acceptance_determinism"] = None
        coverage["acceptance_determinism"] = "not-measurable"
        judge.append({"dimension": "acceptance_determinism", "reason": "no identifiable acceptance section in prose"})

    # context locality
    per_task = []
    amplifs = []
    for t in parsed["tasks"]:
        n = len(t["files"])
        per_task.append({"task_text": t["text"][:80], "context_files": n})
        if n:
            amplifs.append(float(n))
    out["context_locality"] = {
        "amplification_proxy": round(sum(amplifs) / len(amplifs), 3) if amplifs else None,
        "per_task": per_task,
        "max_context_files": max((len(t["files"]) for t in parsed["tasks"]), default=0),
        "bare_directories": [],
        "note": "proxy = files mentioned per task (owned paths are not declared in prose plans)",
    }
    coverage["context_locality"] = "partial" if amplifs else "not-measurable"

    # ownership collisions: detect only when parallel markers + shared file co-occur
    collisions = {"benign": 0, "serialized": 0, "hazardous": 0, "details": []}
    if parsed["parallel_marker_any"]:
        file_tasks = {}
        for t in parsed["tasks"]:
            for f in t["files"]:
                file_tasks.setdefault(f, []).append(t["text"][:60])
        for f, txts in file_tasks.items():
            if len(txts) > 1:
                collisions["hazardous"] += 1
                collisions["details"].append({"shared_path": f, "parallel_tasks": len(txts),
                                              "note": "parallel marker present + same file in multiple tasks"})
    else:
        coverage["ownership_collisions"] = "not-measurable"
    out["ownership_collisions"] = collisions
    coverage.setdefault("ownership_collisions", "assessed")

    # dependency precision
    def tasks_mentioning(anchor_id):
        files = [a["files"][0] for a in case["anchors"] if a["id"] == anchor_id]
        res = []
        for t in parsed["tasks"]:
            if any(f in t["files"] for f in files):
                res.append(t)
        return res

    def order_phrase_between(frm_files, to_files):
        for o in parsed["explicit_ordering"]:
            lf, tf = o["later"].lower(), o["earlier"].lower()
            if any(f.lower() in tf or f.split("/")[-1].lower() in tf for f in frm_files) and \
               any(f.lower() in lf or f.split("/")[-1].lower() in lf for f in to_files):
                return o
        return None

    mnh_details, mnh_violated = [], 0
    for spec in expected.get("must_not_have_edges", []):
        a_files = case_anchor_files(case, spec["from_anchor"])
        b_files = case_anchor_files(case, spec["to_anchor"])
        ta, tb = tasks_mentioning(spec["from_anchor"]), tasks_mentioning(spec["to_anchor"])
        violation = None
        explicit = order_phrase_between(a_files, b_files) or order_phrase_between(b_files, a_files)
        if explicit:
            violation = f"explicit ordering phrase: {explicit['form']}"
        elif ta and tb and parsed["implied_order_pairs"] and not parsed["parallel_marker_any"]:
            # linear checklist implies serialization
            violation = "linear checklist order implies serialization (no parallel marker anywhere)"
        mnh_violated += int(violation is not None)
        mnh_details.append({"from": spec["from_anchor"], "to": spec["to_anchor"],
                            "violated": bool(violation), "reason": spec["reason"], "evidence": violation})
    mh_details, mh_hit = [], 0
    for spec in expected.get("must_have_edges", []):
        ta, tb = tasks_mentioning(spec["from_anchor"]), tasks_mentioning(spec["to_anchor"])
        via = None
        if any(t in ta for t in tb):
            via = "single task mentions both anchors"
        elif order_phrase_between(case_anchor_files(case, spec["from_anchor"]),
                                  case_anchor_files(case, spec["to_anchor"])):
            via = "explicit ordering phrase"
        mh_hit += int(via is not None)
        mh_details.append({"from": spec["from_anchor"], "to": spec["to_anchor"],
                           "hit": via is not None, "via": via})
    out["dependency_precision"] = {
        "must_have": {"hit": mh_hit, "total": len(expected.get("must_have_edges", [])), "details": mh_details},
        "must_not_have": {"violated": mnh_violated, "total": len(expected.get("must_not_have_edges", [])), "details": mnh_details},
        "cycles": 0,
        "edges_without_reason": None,
        "unknown_task_edges": 0,
    }
    coverage["dependency_precision"] = "partial"

    # integration explicitness
    itx = parsed["integration_text"].lower()
    has_e2e = bool(re.search(r"end.to.end|e2e|full (flow|pipeline)|integration test|wiring (test|step)", itx or plan_text.lower()))
    has_integration_task = bool(re.search(r"integration (step|task|phase|stage)", itx or plan_text.lower()))
    score = (1.0 if (has_e2e and has_integration_task) else 0.5 if (has_e2e or has_integration_task) else 0.0)
    out["integration_explicitness"] = {
        "score": score,
        "by_kind": {"contract_consistency": 0, "seam_integration": int(has_integration_task),
                    "e2e_closure": int(has_e2e), "final_acceptance": 0},
        "e2e_gates": int(has_e2e),
        "failure_gates": 0,
        "fixes_owned": 0,
        "case_requirements_met": None,
        "note": "keyword-level detection only; prose does not declare gate structure",
    }
    coverage["integration_explicitness"] = "partial"

    # leaf boundedness
    phase = [t["text"][:60] for t in parsed["tasks"] if len(t["files"]) >= 3]
    out["leaf_boundedness"] = {
        "phase_shaped_leaves": phase,
        "max_anchors_per_task_observed": max((len({a["id"] for a in case["anchors"]
                                                  if any(f in t["files"] for f in a["files"])}) for t in parsed["tasks"]), default=0),
        "over_anchor_cap": sum(1 for p in phase),
        "note": "anchor coverage per task from file mentions",
    }
    coverage["leaf_boundedness"] = "partial" if parsed["tasks"] else "not-measurable"

    # recoverability: not expressible in prose V1
    out["recoverability"] = {"score": None, "per_anchor": []}
    coverage["recoverability"] = "not-measurable"
    judge.append({"dimension": "recoverability", "reason": "prose plans do not declare checkpoint/recovery structure"})

    # scope discipline
    creep, named = [], []
    oos = parsed["out_of_scope_text"].lower()
    task_blob = " ".join(t["text"].lower() for t in parsed["tasks"])
    for p in expected.get("must_not_expand_scope", []):
        base = p.split("/")[-1].lower()
        in_task = p.lower() in task_blob or base in task_blob
        in_oos = p.lower() in oos or base in oos
        if in_task:
            creep.append(p)
        if in_oos:
            named.append(p)
    out["scope_discipline"] = {
        "creep_items_planned": creep,
        "out_of_scope_named": named,
        "score": round(1 - len(creep) / len(expected.get("must_not_expand_scope", [])), 4)
        if expected.get("must_not_expand_scope") else 1.0,
    }
    coverage["scope_discipline"] = "assessed" if expected.get("must_not_expand_scope") else "not-measurable"

    # task count
    rng = expected.get("acceptable_task_count_range")
    n = len(parsed["tasks"])
    out["task_count"] = {
        "actual": n if n else None,
        "range": rng,
        "in_range": (rng[0] <= n <= rng[1]) if (rng and n) else None,
    }

    # gaming guards (prose-applicable subset)
    flags = []
    if rng and n and n > rng[1]:
        flags.append({"code": "G1_OVER_FRAGMENTED", "detail": f"{n} task lines > range max {rng[1]}"})
    if not parsed["parallel_marker_any"] and expected.get("parallelizable_groups"):
        flags.append({"code": "G2_ALL_SERIAL", "detail": "no parallelism mentioned anywhere in the plan"})
    if parsed["tasks"]:
        zero = sum(1 for t in parsed["tasks"] if not t["files"])
        if zero / len(parsed["tasks"]) > 0.5:
            flags.append({"code": "G3_CONTEXT_STARVATION", "detail": f"{zero}/{len(parsed['tasks'])} task lines mention no repo file"})
    out["gaming_flags"] = flags

    out["judge_pending"] = judge
    out["metric_coverage"] = coverage
    return out


def case_anchor_files(case: dict, anchor_id: str) -> list[str]:
    for a in case["anchors"]:
        if a["id"] == anchor_id:
            return a["files"]
    return []
