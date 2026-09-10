#!/usr/bin/env python3
"""plan-check — deterministic gate for Long-Task Planning artifacts.

Zero-dependency (stdlib only), cross-platform. Run via:

    uv run --no-project python plan-check.py <subcommand>

Subcommands:
    validate <file.json>        Validate one artifact against its declared schema.
    lint <plan-dir>             Cross-artifact deterministic checks; JSON findings on stdout.
    report <plan-dir>           Human-readable plan summary.
    selftest                    Built-in negative tests for validator + core lint logic.

Exit codes: 0 = clean, 1 = validation errors / findings at or above --fail-on,
2 = usage or IO error.

The mini JSON-Schema validator supports exactly the keyword subset used by the
schemas in ../schemas/planning/:
    type (incl. list-of-types), required, properties, additionalProperties,
    items, enum, const, pattern, minLength, maxLength, minItems, maxItems,
    minimum, maximum.
If a schema starts using other keywords, extend _check_* here first — the
validator must stay explainable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA_TO_FILE = {
    "planning/stage-contract@2": "stage-contract.schema.json",
    "planning/candidate-tasks@1": "candidate-tasks.schema.json",
    "planning/dag@2": "dag.schema.json",
    "planning/integration-plan@2": "integration-plan.schema.json",
    "planning/task-package@2": "task-package.schema.json",
    "planning/risk-estimates@1": "risk-estimates.schema.json",
    "planning/audit@2": "audit.schema.json",
    "planning/checkpoint@1": "checkpoint.schema.json",
    "planning/replan-request@1": "replan-request.schema.json",
    "planning/run-manifest@1": "run-manifest.schema.json",
    "planning/repo-context-snapshot@1": "repo-context-snapshot.schema.json",
}

DEFAULT_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas" / "planning"

# Vague-acceptance phrase list (heuristic; see docs for the deterministic rule:
# any hit in acceptance text is a MAJOR finding the auditor must confirm or
# justify away). English phrases are matched case-insensitively with word
# boundaries where practical; Chinese phrases by substring.
VAGUE_EN = [
    r"\bensure[sd]?\s+it\s+works\b",
    r"\bworks\s+(?:correctly|as\s+expected|fine)\b",
    r"\bproperly\b",
    r"\breasonably\b",
    r"\bas\s+(?:needed|appropriate)\b",
    r"\bsufficiently\b",
    r"\brobustly\b",
    r"\bseamlessly\b",
    r"\bpolish(?:ing|ed)?\b",
    r"\bclean\s*up\b",
    r"\btidy\s*up\b",
    r"\boptimize[sd]?\b",
    r"\bimprove[sd]?\s+(?:the|this)\b",
    r"\buser[\s-]friendly\b",
    r"\bgood\s+enough\b",
]
VAGUE_ZH = [
    "确保正常", "正常工作", "运行正常", "充分测试", "合理处理", "尽可能",
    "完善", "优化", "基本完成", "大致完成", "应该没问题", "没什么问题",
]
# Acceptance text must contain at least one observable-evidence marker, or be
# long enough to describe an observable behavior (heuristic, MINOR).
EVIDENCE_MARKERS = re.compile(
    r"\b(?:returns?|return|raises?|raise|exits?|exit|prints?|print|writes?|write|"
    r"creates?|create|fails?|fail|asserts?|assert|status|code|exit code|HTTP|"
    r"row|records?|record|file|test|pytest|logs?|log|contains?|emit[sd]?|emits|emitted)\b|"
    r"返回|抛出|退出码|状态码|测试|写入|创建|记录|断言",
    re.IGNORECASE,
)
# Outcome verbs a leaf objective must use (a "implement X feature" bare line is
# the anti-pattern of doc 2.5).
OUTCOME_VERBS = re.compile(
    r"\b(?:implement|add|create|write|build|extend|replace|remove|refactor|"
    r"migrate|wire|expose|verify|test|close|implement|extract|integrate|"
    r"enforce|persist|schedule|recover|register|hook|run|runs|fix|fixes|"
    r"execute|executes|sweep|diff|collect|collects|audit|audits)\b|"
    r"实现|新增|创建|编写|改造|替换|移除|迁移|接线|校验|测试|闭合|持久化|注册|挂载|运行|修复|执行|审计",
    re.IGNORECASE,
)

BROAD_CONTEXT_FILE_THRESHOLD = 25  # more than this many required files = broad

TASK_ID_RE = re.compile(r"^T[0-9]{2,}$")
INTEGRATION_KINDS = ("contract_consistency", "seam_integration", "e2e_closure", "final_acceptance")


def _norm_path(p) -> str:
    """Normalize a plan path: drop the ' (new)' annotation and slashes."""
    return str(p).replace("\\", "/").split(" (")[0].strip("/")


# ---------------------------------------------------------------------------
# Mini JSON-Schema validator (documented keyword subset)
# ---------------------------------------------------------------------------

def _type_ok(value, t: str) -> bool:
    return {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }[t](value)


def _check(instance, schema: dict, path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        return
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum {schema['enum']!r}")
        return
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            errors.append(f"{path}: type is {type(instance).__name__}, expected {'|'.join(types)}")
            return
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match pattern {schema['pattern']!r}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array has {len(instance)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: array has {len(instance)} items > maxItems {schema['maxItems']}")
        if "items" in schema:
            for i, item in enumerate(instance):
                _check(item, schema["items"], f"{path}[{i}]", errors)
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required key {req!r}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                _check(value, props[key], f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected key {key!r}")
    # NOTE: we intentionally do NOT flag unknown keywords in the schema; the
    # subset is enforced by code review of the schema files.


def validate_against(instance, schema: dict) -> list[str]:
    errors: list[str] = []
    _check(instance, schema, "$", errors)
    return errors


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, "file not found"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"


def _load_schema(schemas_dir: Path, kind: str) -> tuple[dict | None, str | None]:
    fname = SCHEMA_TO_FILE.get(kind)
    if fname is None:
        return None, f"unknown schema kind {kind!r}"
    data, err = _load_json(schemas_dir / fname)
    if err:
        return None, err
    return data, None


def validate_file(path: Path, schemas_dir: Path) -> dict:
    data, err = _load_json(path)
    if err:
        return {"file": str(path), "ok": False, "errors": [err]}
    kind = data.get("schema") if isinstance(data, dict) else None
    if not isinstance(kind, str) or kind not in SCHEMA_TO_FILE:
        return {
            "file": str(path), "ok": False,
            "errors": ["artifact has no valid 'schema' field (expected planning/<kind>@N)"],
        }
    schema, err = _load_schema(schemas_dir, kind)
    if err:
        return {"file": str(path), "ok": False, "errors": [f"schema lookup failed: {err}"]}
    errors = validate_against(data, schema)
    return {"file": str(path), "schema": kind, "ok": not errors, "errors": errors}


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def has_cycle(tasks: list[str], edges: list[dict]) -> list[str] | None:
    """Return one cycle as a task list, or None. Iterative DFS, 3-color."""
    adj: dict[str, list[str]] = {t: [] for t in tasks}
    for e in edges:
        if e["from"] in adj and e["to"] in adj:
            adj[e["from"]].append(e["to"])
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t: WHITE for t in tasks}
    for start in tasks:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(adj[start]))]
        color[start] = GRAY
        path = [start]
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if color[nxt] == GRAY:
                    return path[path.index(nxt):] + [nxt]
                if color[nxt] == WHITE:
                    color[nxt] = GRAY
                    stack.append((nxt, iter(adj[nxt])))
                    path.append(nxt)
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                stack.pop()
                path.pop()
    return None


def reachability(tasks: list[str], edges: list[dict]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {t: set() for t in tasks}
    for e in edges:
        if e["from"] in adj and e["to"] in adj:
            adj[e["from"]].add(e["to"])
    reach: dict[str, set[str]] = {}
    for t in tasks:
        seen: set[str] = set()
        stack = [t]
        while stack:
            cur = stack.pop()
            for nxt in adj.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        reach[t] = seen
    return reach


def longest_path_hops(tasks: list[str], edges: list[dict]) -> int:
    """Longest chain in unit weights (DAG assumed; cycle handled by caller)."""
    adj: dict[str, set[str]] = {t: set() for t in tasks}
    indeg = {t: 0 for t in tasks}
    for e in edges:
        if e["from"] in adj and e["to"] in adj and e["to"] not in adj[e["from"]]:
            adj[e["from"]].add(e["to"])
            indeg[e["to"]] += 1
    memo: dict[str, int] = {}
    def dp(t: str) -> int:
        if t in memo:
            return memo[t]
        best = 0
        for nxt in adj[t]:
            best = max(best, 1 + dp(nxt))
        memo[t] = best
        return best
    # memoized recursion is safe on a DAG; topological order not required
    sys.setrecursionlimit(10000)
    return max((dp(t) for t in tasks), default=0) + (1 if tasks else 0)


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

class Plan:
    def __init__(self, plan_dir: Path, schemas_dir: Path):
        self.plan_dir = plan_dir
        self.schemas_dir = schemas_dir
        self.findings: list[dict] = []
        self.snapshot = None
        self.contract = None
        self.candidates = None
        self.dag = None
        self.integration = None
        self.risk = None
        self.audit = None
        self.packages: dict[str, dict] = {}

    def add(self, code: str, severity: str, artifact: str, detail: str, task_id: str | None = None):
        self.findings.append({
            "code": code, "severity": severity, "artifact": artifact,
            "task_id": task_id, "detail": detail,
        })

    def load(self) -> bool:
        """Load all core artifacts; schema-invalid ones become BLOCKERs."""
        core = {
            "snapshot": "repo-context-snapshot.json",
            "contract": "stage-contract.json",
            "candidates": "candidate-tasks.json",
            "dag": "dag.json",
            "integration": "integration-plan.json",
            "risk": "risk-estimates.json",
            "audit": "audit.json",
        }
        for attr, fname in core.items():
            path = self.plan_dir / fname
            if not path.exists():
                continue
            res = validate_file(path, self.schemas_dir)
            if not res["ok"]:
                for e in res["errors"]:
                    self.add("SCHEMA_INVALID", "BLOCKER", fname, e)
                setattr(self, attr, None)
            else:
                with open(path, "r", encoding="utf-8") as fh:
                    setattr(self, attr, json.load(fh))
        tasks_dir = self.plan_dir / "tasks"
        if tasks_dir.is_dir():
            for path in sorted(tasks_dir.glob("*.json")):
                res = validate_file(path, self.schemas_dir)
                if not res["ok"]:
                    for e in res["errors"]:
                        self.add("SCHEMA_INVALID", "BLOCKER", f"tasks/{path.name}", e)
                    continue
                with open(path, "r", encoding="utf-8") as fh:
                    pkg = json.load(fh)
                self.packages[pkg["task_id"]] = pkg
        return self.contract is not None

    def task_ids(self) -> list[str]:
        """Union of candidate leaves and integration tasks (single-writer rule:
        candidate-tasks.json owns leaves, integration-plan.json owns integration
        tasks; both are nodes of the DAG)."""
        if not self.candidates:
            return []
        ids = [t["id"] for t in self.candidates["tasks"]]
        if self.integration:
            for it in self.integration["integration_tasks"]:
                if it["task_id"] not in ids:
                    ids.append(it["task_id"])
        return ids

    def candidate_ids(self) -> list[str]:
        if not self.candidates:
            return []
        return [t["id"] for t in self.candidates["tasks"]]

    def _new_wiring_present(self) -> bool:
        """Conservative proxy for 'this Stage may add production wiring'.

        P1-4: We no longer auto-prove omission is safe because "all new files
        are in a fresh directory". If the Stage has multiple leaves and defines
        seams, we CANNOT assume fresh directory proves no wiring — we return
        True if:
        (a) a new file lands in a directory that already contains another
            task's files (actual cross-task wiring), OR
        (b) multiple leaves create new files and seams are defined (we
            cannot prove absence of wiring without the grounded auditor).

        The fresh-directory justification alone is insufficient. The grounded
        auditor must confirm wiring is absent."""
        if self.snapshot is None or not self.candidates:
            return False
        # Need multiple leaves and seams to have integration work
        if len(self.candidates["tasks"]) < 2:
            return False
        if not self.contract:
            return False
        if not self.contract.get("integration_seams"):
            return False

        snap_paths = {f["path"].replace("\\", "/").strip("/")
                      for f in self.snapshot.get("files", [])}
        # Track which directories already have files (from snapshot = existing repo)
        existing_dirs = set()
        for p in snap_paths:
            d = p.rsplit("/", 1)[0] if "/" in p else ""
            if d:
                existing_dirs.add(d)
        # Check: do any tasks create new files in directories that already
        # exist in the repo (i.e., the directory had other files before)?
        # Also: do multiple tasks create new files? (cross-task wiring risk)
        tasks_with_new_files = 0
        for t in self.candidates["tasks"]:
            has_new = False
            for p in t["owned_paths"]:
                np = _norm_path(p)
                if np not in snap_paths:
                    has_new = True
                    # Check if this new file goes into an existing directory
                    d = np.rsplit("/", 1)[0] if "/" in np else ""
                    if d in existing_dirs:
                        # New file in existing directory = actual wiring risk
                        return True
            if has_new:
                tasks_with_new_files += 1
        # P1-4: Multiple tasks creating new files + seams defined
        # cannot auto-prove "no wiring" even if all are in fresh directories
        if tasks_with_new_files >= 2:
            return True
        return False

    def run(self) -> list[dict]:
        ids = self.task_ids()
        cand_ids = self.candidate_ids()
        idset = set(ids)
        tasks_by_id = {t["id"]: t for t in (self.candidates["tasks"] if self.candidates else [])}
        edges = self.dag["edges"] if self.dag else []

        # --- completeness -------------------------------------------------
        if self.contract is None:
            self.add("MISSING_ARTIFACT", "BLOCKER", "stage-contract.json",
                     "stage-contract.json missing or invalid — nothing else can be checked")
            return self.findings
        for fname in ("candidate-tasks.json", "dag.json", "integration-plan.json"):
            if not (self.plan_dir / fname).exists():
                self.add("MISSING_ARTIFACT", "BLOCKER", fname,
                         "core artifact missing; plan is incomplete (stage-contract exists)")
        if not (self.plan_dir / "repo-context-snapshot.json").exists():
            self.add("MISSING_ARTIFACT", "BLOCKER", "repo-context-snapshot.json",
                     "stage-0 artifact missing — planner and auditor have no repo grounding")
        if not ids:
            return self.findings
        for tid in ids:
            if tid not in self.packages:
                self.add("MISSING_TASK_PACKAGE", "BLOCKER", "tasks/",
                         f"candidate task {tid} has no tasks/{tid}.json package", tid)
        for tid in self.packages:
            if tid not in idset:
                self.add("ORPHAN_TASK_PACKAGE", "MINOR", "tasks/",
                         f"package {tid} exists but no such candidate task", tid)

        # --- duplicate ids ------------------------------------------------
        seen: set[str] = set()
        for t in (self.candidates["tasks"] if self.candidates else []):
            if t["id"] in seen:
                self.add("DUPLICATE_TASK_ID", "BLOCKER", "candidate-tasks.json",
                         f"duplicate task id {t['id']}", t["id"])
            seen.add(t["id"])
        if self.integration:
            for it in self.integration["integration_tasks"]:
                if it["task_id"] in seen:
                    self.add("DUPLICATE_TASK_ID", "BLOCKER", "integration-plan.json",
                             f"integration task id {it['task_id']} collides with a candidate "
                             f"leaf id", it["task_id"])
                seen.add(it["task_id"])

        # --- DAG structure --------------------------------------------------
        if self.dag is not None:
            unknown = sorted({e[k] for e in edges for k in ("from", "to")} - idset)
            for u in unknown:
                self.add("DAG_UNKNOWN_TASK", "BLOCKER", "dag.json",
                         f"edge references unknown task {u}")
            cycle = has_cycle(ids, edges)
            if cycle:
                self.add("DAG_CYCLE", "BLOCKER", "dag.json",
                         "cycle: " + " -> ".join(cycle))
            else:
                declared = self.dag["critical_path"]
                decl_ok = all(
                    any(e["from"] == a and e["to"] == b for e in edges)
                    for a, b in zip(declared, declared[1:])
                )
                if not decl_ok and len(declared) > 1:
                    self.add("CRITICAL_PATH_INVALID", "MAJOR", "dag.json",
                             "declared critical path is not a real edge chain")
                elif decl_ok:
                    longest = longest_path_hops(ids, edges)
                    if len(declared) < longest:
                        self.add("CRITICAL_PATH_INVALID", "MAJOR", "dag.json",
                                 f"declared critical path has {len(declared)} hops but the DAG "
                                 f"contains a chain of {longest} hops")
            for group in self.dag.get("parallel_groups", []):
                for i, a in enumerate(group):
                    for b in group[i + 1:]:
                        if a in idset and b in idset and (
                            any(e["from"] == a and e["to"] == b for e in edges)
                            or any(e["from"] == b and e["to"] == a for e in edges)
                        ):
                            self.add("PARALLEL_GROUP_INCONSISTENT", "MAJOR", "dag.json",
                                     f"parallel group contains ordered pair {a},{b}")
            for g in self.dag.get("integration_gates", []):
                if g["task_id"] not in idset:
                    self.add("DAG_UNKNOWN_TASK", "BLOCKER", "dag.json",
                             f"integration gate references unknown task {g['task_id']}")

        # --- ownership collisions (unordered candidate tasks, overlapping paths)
        reach = reachability(ids, edges)
        cand = tasks_by_id
        for i, a in enumerate(cand_ids):
            for b in cand_ids[i + 1:]:
                if b in reach[a] or a in reach[b]:
                    continue  # ordered — sequencing resolves the overlap
                for pa in cand[a]["owned_paths"]:
                    for pb in cand[b]["owned_paths"]:
                        pa2, pb2 = pa.rstrip("/"), pb.rstrip("/")
                        if pa2 == pb2 or pa2.startswith(pb2 + "/") or pb2.startswith(pa2 + "/"):
                            self.add("OWNERSHIP_COLLISION_PARALLEL", "BLOCKER",
                                     "candidate-tasks.json",
                                     f"unordered tasks {a},{b} both own overlapping path "
                                     f"{pa} / {pb} — parallel execution would conflict", a)
                            break
                    else:
                        continue
                    break

        # --- contracts ------------------------------------------------------
        contract_ids = {c["id"] for c in self.contract.get("shared_contracts", [])}
        frozen = {c["id"] for c in self.contract.get("shared_contracts", []) if c.get("frozen")}
        unlock = {}
        if self.dag:
            for u in self.dag.get("unlock_contracts", []):
                unlock[u["contract_id"]] = set(u["unlocks"])
        owners = {b["contract_id"]: b["owner_task"]
                  for b in (self.dag.get("contract_bindings", []) if self.dag else [])}
        for tid in cand_ids:
            t = cand[tid]
            for cid in t["required_context"]["contracts"]:
                if cid not in contract_ids:
                    self.add("CONTRACT_UNKNOWN", "MAJOR", "candidate-tasks.json",
                             f"task {tid} consumes unknown contract {cid}", tid)
                    continue
                owner = owners.get(cid, "")
                if owner in idset and owner != tid and owner not in reach[tid] and tid not in reach[owner]:
                    if cid not in frozen:
                        self.add("CONTRACT_CONSUMED_BEFORE_OWNER", "MAJOR",
                                 "candidate-tasks.json",
                                 f"task {tid} consumes contract {cid} owned by {owner} without "
                                 f"ordering and the contract is not frozen", tid)
                    elif tid not in unlock.get(cid, set()):
                        self.add("UNLOCK_NOT_DECLARED", "MINOR", "dag.json",
                                 f"task {tid} uses frozen contract {cid} in parallel with owner "
                                 f"{owner} but unlock_contracts does not list it", tid)

        # --- stage-1/stage-3 separation: no task ids in the stage contract ----
        # The stage contract may only name LOGICAL owners/participants; concrete
        # task ids are produced by context-decomposition and bound in the DAG.
        for c in self.contract.get("shared_contracts", []):
            lo = str(c.get("logical_owner", ""))
            if TASK_ID_RE.match(lo):
                self.add("CONTRACT_OWNER_TASK_ID", "BLOCKER", "stage-contract.json",
                         f"contract {c['id']} logical_owner is a task id ({lo!r}) — stage 1 must "
                         f"name a logical responsibility; the DAG stage binds it to a concrete task")
        for s in self.contract.get("integration_seams", []):
            for p in s.get("participants", []):
                if TASK_ID_RE.match(str(p)):
                    self.add("SEAM_PARTICIPANT_TASK_ID", "BLOCKER", "stage-contract.json",
                             f"seam {s['id']} participant {p!r} is a task id — seams name logical "
                             f"participants (components/roles); the DAG stage binds them")

        # --- bindings: every logical owner / seam participant maps to real tasks
        if self.dag is not None:
            cb = self.dag.get("contract_bindings", [])
            sb = self.dag.get("seam_bindings", [])
            cids_all = {c["id"] for c in self.contract.get("shared_contracts", [])}
            sids_all = {s["id"] for s in self.contract.get("integration_seams", [])}
            for c in self.contract.get("shared_contracts", []):
                hits = [b for b in cb if b.get("contract_id") == c["id"]]
                if not hits:
                    self.add("UNBOUND_CONTRACT", "BLOCKER", "dag.json",
                             f"contract {c['id']} (logical_owner {str(c.get('logical_owner'))!r}) "
                             f"has no contract_bindings entry — every contract needs a concrete "
                             f"owner task before the plan is complete")
                elif len(hits) > 1:
                    self.add("UNBOUND_CONTRACT", "MAJOR", "dag.json",
                             f"contract {c['id']} has {len(hits)} contract_bindings entries "
                             f"(exactly one required)")
                elif hits[0].get("owner_task") not in idset:
                    self.add("UNBOUND_CONTRACT", "BLOCKER", "dag.json",
                             f"contract {c['id']} is bound to unknown task "
                             f"{hits[0].get('owner_task')!r}")
            for b in cb:
                if b.get("contract_id") not in cids_all:
                    self.add("UNBOUND_CONTRACT", "MAJOR", "dag.json",
                             f"contract_bindings references unknown contract "
                             f"{b.get('contract_id')!r}")
            for s in self.contract.get("integration_seams", []):
                hits = [b for b in sb if b.get("seam_id") == s["id"]]
                if not hits:
                    self.add("UNBOUND_SEAM", "BLOCKER", "dag.json",
                             f"seam {s['id']} (participants {s.get('participants')}) has no "
                             f"seam_bindings entry — every seam needs concrete participant tasks")
                elif len(hits) > 1:
                    self.add("UNBOUND_SEAM", "MAJOR", "dag.json",
                             f"seam {s['id']} has {len(hits)} seam_bindings entries (exactly one required)")
                else:
                    pts = hits[0].get("participant_tasks", [])
                    if len(set(pts)) < 2:
                        self.add("UNBOUND_SEAM", "BLOCKER", "dag.json",
                                 f"seam {s['id']} is bound to fewer than 2 distinct tasks: {pts}")
                    for t in pts:
                        if t not in idset:
                            self.add("UNBOUND_SEAM", "BLOCKER", "dag.json",
                                     f"seam {s['id']} participant binding references unknown task {t!r}")
            for b in sb:
                if b.get("seam_id") not in sids_all:
                    self.add("UNBOUND_SEAM", "MAJOR", "dag.json",
                             f"seam_bindings references unknown seam {b.get('seam_id')!r}")

        # --- repo grounding: snapshot vs plan (hidden dependencies) -----------
        if self.snapshot is not None:
            snap_files = {f["path"].replace("\\", "/").strip("/"): f
                          for f in self.snapshot.get("files", [])}
            shared_files = set(self.snapshot.get("known_shared_files", []))
            flagged: set[tuple[str, str]] = set()
            for tid in cand_ids:
                for f in cand[tid]["required_context"]["files"]:
                    np = _norm_path(f)
                    is_dir = str(f).rstrip().endswith("/") or "." not in np.rsplit("/", 1)[-1]
                    if " (new" not in f and not is_dir and np not in snap_files:
                        self.add("CONTEXT_FILE_NOT_IN_SNAPSHOT", "MAJOR",
                                 "candidate-tasks.json",
                                 f"task {tid} context file {f!r} is not in the repo snapshot and "
                                 f"is not marked (new) — typo, wrong path, or an unscanned area", tid)
            for tid in cand_ids:
                declared = {_norm_path(f) for f in cand[tid]["required_context"]["files"]}
                declared |= {_norm_path(p) for p in cand[tid]["owned_paths"]}
                for f in cand[tid]["required_context"]["files"]:
                    sf = snap_files.get(_norm_path(f))
                    if not sf:
                        continue
                    for imp in sf.get("imports", []):
                        key = (tid, imp)
                        if imp in declared or key in flagged:
                            continue
                        flagged.add(key)
                        sev = "BLOCKER" if imp in shared_files else "MAJOR"
                        self.add("HIDDEN_DEPENDENCY", sev, "candidate-tasks.json",
                                 f"task {tid} context file {f} imports {imp} (per repo snapshot) "
                                 f"but the task neither declares nor owns it"
                                 + (" — known shared core file" if sev == "BLOCKER" else ""), tid)

        # --- frozen contract snapshots in packages (self-containedness) -------
        contracts_by_id = {c["id"]: c for c in self.contract.get("shared_contracts", [])}
        for tid, pkg in self.packages.items():
            inlined = {fc.get("contract_id"): fc for fc in pkg.get("frozen_contracts", [])}
            for cid in pkg.get("required_context", {}).get("contracts", []):
                if cid not in inlined:
                    self.add("CONTRACT_NOT_INLINED", "MAJOR", f"tasks/{tid}.json",
                             f"task {tid} consumes contract {cid} but its package does not inline "
                             f"the frozen spec — the executor would have to read stage-contract.json",
                             tid)
            for fc in pkg.get("frozen_contracts", []):
                cid = fc.get("contract_id")
                cur = contracts_by_id.get(cid)
                if cur is None:
                    self.add("CONTRACT_UNKNOWN", "MAJOR", f"tasks/{tid}.json",
                             f"package {tid} inlines unknown contract {cid}", tid)
                    continue
                cur_spec = cur.get("spec", "")
                if fc.get("spec") != cur_spec:
                    self.add("STALE_CONTRACT_SNAPSHOT", "BLOCKER", f"tasks/{tid}.json",
                             f"package {tid} inlined contract {cid} with a spec that differs from "
                             f"the current stage-contract spec — re-package after contract changes",
                             tid)
                elif fc.get("source_hash") != "sha256:" + hashlib.sha256(
                        cur_spec.encode("utf-8")).hexdigest():
                    self.add("STALE_CONTRACT_SNAPSHOT", "BLOCKER", f"tasks/{tid}.json",
                             f"package {tid} source_hash for contract {cid} does not match the "
                             f"current stage-contract spec (contract changed after packaging)", tid)

        # --- acceptance text (vague phrases) --------------------------------
        def scan_text(text: str, where: str, tid: str | None, code_prefix=""):
            if not isinstance(text, str):
                return
            for pat in VAGUE_EN:
                if re.search(pat, text, re.IGNORECASE):
                    self.add("VAGUE_ACCEPTANCE", "MAJOR", where,
                             f"vague acceptance language ({pat!r}) in: {text[:120]}", tid)
                    return
            for zh in VAGUE_ZH:
                if zh in text:
                    self.add("VAGUE_ACCEPTANCE", "MAJOR", where,
                             f"vague acceptance language ({zh!r}) in: {text[:120]}", tid)
                    return
            if not EVIDENCE_MARKERS.search(text):
                self.add("VAGUE_ACCEPTANCE", "MINOR", where,
                         f"acceptance text has no observable-evidence marker: {text[:120]}", tid)

        for a in self.contract.get("acceptance", []):
            for field in ("description", "positive_case", "negative_case", "failure_behavior"):
                scan_text(a.get(field, ""), "stage-contract.json", None)
        for tid, pkg in self.packages.items():
            for at in pkg.get("acceptance_tests", []):
                scan_text(at.get("description", ""), f"tasks/{tid}.json", tid)
                scan_text(at.get("evidence", ""), f"tasks/{tid}.json", tid)
            for fc in pkg.get("failure_cases", []):
                scan_text(fc.get("expected_behavior", ""), f"tasks/{tid}.json", tid)

        # --- bare objectives (candidate view + executor view) ----------------
        for tid in cand_ids:
            obj = cand[tid]["objective"]
            if len(obj) < 40 or not OUTCOME_VERBS.search(obj):
                self.add("BARE_OBJECTIVE", "MAJOR", "candidate-tasks.json",
                         f"objective of {tid} reads like an unexecutable one-liner: {obj[:120]}", tid)
        for tid, pkg in self.packages.items():
            obj = pkg.get("objective", "")
            if len(obj) < 40 or not OUTCOME_VERBS.search(obj):
                self.add("BARE_OBJECTIVE", "MAJOR", f"tasks/{tid}.json",
                         f"package objective of {tid} reads like an unexecutable one-liner: "
                         f"{obj[:120]}", tid)

        # --- broad context loading -------------------------------------------
        for tid in cand_ids:
            files = cand[tid]["required_context"]["files"]
            if len(files) > BROAD_CONTEXT_FILE_THRESHOLD:
                self.add("BROAD_CONTEXT_LOADING", "MAJOR", "candidate-tasks.json",
                         f"task {tid} requires {len(files)} context files — likely not context-"
                         f"bounded; re-check the closure", tid)
            for f in files:
                if f in ("", ".", "/", "app", "src") :
                    self.add("BROAD_CONTEXT_LOADING", "MAJOR", "candidate-tasks.json",
                             f"task {tid} lists a bare top-level directory as context: {f!r}", tid)
                    break

        # --- integration explicitness (present / merged / omitted / missing) ---
        if self.integration is not None:
            present: set[str] = set()
            merged: set[str] = set()
            for it in self.integration.get("integration_tasks", []):
                k = it["kind"]
                if k in INTEGRATION_KINDS:
                    present.add(k)
                for mk in it.get("merged_kinds", []):
                    if mk in INTEGRATION_KINDS:
                        merged.add(mk)
                    if mk == k:
                        self.add("INVALID_INTEGRATION_MERGE", "MAJOR", "integration-plan.json",
                                 f"integration task {it['task_id']} merges its own kind {mk!r} "
                                 f"(merge a DIFFERENT kind into this task, or make it primary)")
            omitted = {o.get("kind") for o in self.integration.get("omitted_kinds", [])
                       if o.get("kind") in INTEGRATION_KINDS}
            for k in sorted(present & merged):
                self.add("INVALID_INTEGRATION_MERGE", "MAJOR", "integration-plan.json",
                         f"integration kind {k!r} is both a primary task kind and merged into "
                         f"another task — pick exactly one satisfaction path")
            for k in sorted(merged & omitted):
                self.add("INVALID_INTEGRATION_MERGE", "MAJOR", "integration-plan.json",
                         f"integration kind {k!r} is merged into a task AND listed in "
                         f"omitted_kinds — pick exactly one satisfaction path")
            # P1-2: present ∩ omitted conflict
            for k in sorted(present & omitted):
                self.add("INVALID_INTEGRATION_MERGE", "MAJOR", "integration-plan.json",
                         f"integration kind {k!r} is both a primary task kind AND listed in "
                         f"omitted_kinds — a present kind cannot also be omitted")

            new_wiring = self._new_wiring_present()
            # P1-3: final closure cannot be satisfied by omission alone
            closure = {"e2e_closure", "final_acceptance"}
            closure_present = bool((present | merged) & closure)
            if not closure_present:
                self.add("NO_INTEGRATION_GATE", "BLOCKER", "integration-plan.json",
                         "no real integration task of kind e2e_closure or final_acceptance "
                         "exists — omission alone does not satisfy final closure; at least one "
                         "must be present or merged into a real task")
            for kind in INTEGRATION_KINDS:
                if kind in present or kind in merged or kind in omitted:
                    continue
                if kind in closure:
                    continue  # the pair is gated above as one unit
                if kind == "seam_integration":
                    sev = "BLOCKER" if new_wiring else "MAJOR"
                    detail = ("neither present, merged, nor omitted with justification"
                              + (" and new wiring exists (a leaf adds files into an existing "
                                 "seam directory)" if new_wiring else ""))
                else:
                    sev = "MAJOR"
                    detail = "neither present, merged, nor omitted with justification"
                self.add("INTEGRATION_KIND_MISSING", sev, "integration-plan.json",
                         f"integration kind {kind!r} is {detail}")
            if "seam_integration" in omitted and new_wiring:
                # P1-4: Fresh directory no longer auto-proves omission safe.
                # But if an e2e_closure or final_acceptance task already covers
                # the seams, the wiring verification is implicit. Only flag when
                # no closure task covers the seams.
                seams_covered_by_closure = set()
                for it in self.integration.get("integration_tasks", []):
                    if it["kind"] in ("e2e_closure", "final_acceptance"):
                        for s in it.get("seams", []):
                            seams_covered_by_closure.add(s)
                # Check if ALL contract seams are covered by closure tasks
                contract_seams_set = {s["id"] for s in self.contract.get("integration_seams", [])}
                if contract_seams_set - seams_covered_by_closure:
                    # Some seams are NOT covered by closure tasks — flag it
                    self.add("HIDDEN_INTEGRATION_WORK", "BLOCKER", "integration-plan.json",
                             "seam_integration is omitted with justification, but this Stage has "
                             "multiple leaves, defined seams, and new files — the deterministic "
                             "checker cannot prove wiring is absent; the omission must be "
                             "justified by the grounded auditor")
            contract_seams = {s["id"] for s in self.contract.get("integration_seams", [])}
            covered: set[str] = set()
            for s in self.integration.get("seams", []):
                covered.update(s.get("covered_by", []))
                if s["id"] in contract_seams:
                    covered.add(s["id"])
            for sid in contract_seams:
                if sid not in {s["id"] for s in self.integration.get("seams", [])}:
                    self.add("SEAM_UNOWNED", "MAJOR", "integration-plan.json",
                             f"contract seam {sid} has no integration-plan entry")
            for it in self.integration.get("integration_tasks", []):
                for leaf in it.get("owns_fixes_for", []):
                    if leaf in idset and leaf != it["task_id"]:
                        # transitive ordering is enough: the integration task
                        # must run after each leaf it may patch (reachability,
                        # not necessarily a direct edge)
                        if it["task_id"] not in reach.get(leaf, set()):
                            self.add("INTEGRATION_TASK_NOT_IN_DAG", "BLOCKER", "dag.json",
                                     f"integration task {it['task_id']} claims fixes for {leaf} "
                                     f"but no DAG path orders it after {leaf}", it["task_id"])
        else:
            self.add("MISSING_ARTIFACT", "BLOCKER", "integration-plan.json",
                     "integration-plan.json missing or invalid")

        # --- open blocking questions -------------------------------------------
        for q in self.contract.get("open_questions", []):
            if q.get("blocking") and not (q.get("resolution") or "").strip():
                self.add("OPEN_BLOCKING_QUESTION", "BLOCKER", "stage-contract.json",
                         f"blocking question {q['id']} has no resolution: {q['question'][:120]}")

        # --- audit self-consistency ----------------------------------------------
        if self.audit is not None:
            blockers = [f for f in self.findings if f["severity"] == "BLOCKER"]
            if self.audit.get("verdict") == "PASS" and blockers:
                self.add("AUDIT_VERDICT_MISMATCH", "BLOCKER", "audit.json",
                         f"audit verdict is PASS but {len(blockers)} BLOCKER finding(s) exist")

        # --- audit grounding (hard gate — auditor must be grounded + isolated) ---
        if self.audit is not None:
            # P0-3: isolation check
            auditor = self.audit.get("auditor", {})
            if auditor.get("planner_conversation_isolated") is not True:
                self.add("AUDIT_NOT_ISOLATED", "BLOCKER", "audit.json",
                         "audit was not run from an isolated path — "
                         "planner_conversation_isolated must be true; "
                         "a non-isolated audit inherits the planner's blind spots")
            # grounding check
            if self.snapshot is not None:
                g = self.audit.get("grounding")
                if not g:
                    self.add("AUDIT_NOT_GROUNDED", "BLOCKER", "audit.json",
                             "audit records no repo grounding — the auditor must verify plan "
                             "claims against repo-context-snapshot.json and record the snapshot "
                             "revision; grounding is a hard gate")
                elif g.get("repo_revision") and g["repo_revision"] != self.snapshot.get("repo_revision"):
                    self.add("AUDIT_SNAPSHOT_MISMATCH", "BLOCKER", "audit.json",
                             f"audit grounded against snapshot {g.get('repo_revision')!r} but "
                             f"the plan's snapshot is {self.snapshot.get('repo_revision')!r} — "
                             f"the repo moved under the plan; re-snapshot and re-audit")

        # --- risk coverage ------------------------------------------------------
        if self.risk is not None:
            covered = {t["task_id"] for t in self.risk.get("tasks", [])}
            for tid in ids:
                if tid not in covered:
                    self.add("RISK_ESTIMATE_MISSING", "MAJOR", "risk-estimates.json",
                             f"no risk estimate for task {tid}", tid)

        return self.findings


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_validate(args) -> int:
    res = validate_file(Path(args.file), Path(args.schemas_dir))
    _print(res)
    return 0 if res["ok"] else 1


def cmd_lint(args) -> int:
    plan_dir = Path(args.plan_dir)
    if not plan_dir.is_dir():
        print(json.dumps({"error": f"not a directory: {plan_dir}"}))
        return 2
    plan = Plan(plan_dir, Path(args.schemas_dir))
    plan.load()
    findings = plan.run()
    threshold = args.fail_on
    ranked = {"BLOCKER": 3, "MAJOR": 2, "MINOR": 1}
    fail = any(ranked[f["severity"]] >= ranked.get(threshold, 3) for f in findings)
    _print({
        "plan_dir": str(plan_dir),
        "findings": findings,
        "counts": {
            "BLOCKER": sum(1 for f in findings if f["severity"] == "BLOCKER"),
            "MAJOR": sum(1 for f in findings if f["severity"] == "MAJOR"),
            "MINOR": sum(1 for f in findings if f["severity"] == "MINOR"),
        },
        "exit_code": 1 if fail else 0,
    })
    return 1 if fail else 0


def cmd_report(args) -> int:
    plan = Plan(Path(args.plan_dir), Path(args.schemas_dir))
    if not plan.load():
        print("stage-contract.json missing or invalid — cannot report")
        return 2
    ids = plan.task_ids()
    print(f"Stage: {plan.contract.get('stage_id')}")
    print(f"Objective: {plan.contract.get('objective')}")
    print(f"Tasks: {len(ids)} ({', '.join(ids)})")
    if plan.snapshot:
        print(f"Repo snapshot: {plan.snapshot.get('repo_revision')} "
              f"({len(plan.snapshot.get('files', []))} files scanned, "
              f"boundary={plan.snapshot.get('scan_boundary')})")
    print(f"Contracts: {len(plan.contract.get('shared_contracts', []))} "
          f"({sum(1 for c in plan.contract.get('shared_contracts', []) if c.get('frozen'))} frozen)")
    if plan.dag:
        print(f"  contract_bindings: {len(plan.dag.get('contract_bindings', []))}; "
              f"seam_bindings: {len(plan.dag.get('seam_bindings', []))}")
    print(f"Acceptance criteria: {len(plan.contract.get('acceptance', []))}")
    if plan.dag:
        print(f"Edges: {len(plan.dag['edges'])}")
        print("Critical path: " + " -> ".join(plan.dag["critical_path"]))
        for g in plan.dag["parallel_groups"]:
            print(f"Parallel group: {', '.join(g)}")
        print(f"Integration gates: {len(plan.dag.get('integration_gates', []))}")
    if plan.audit:
        print(f"Audit verdict: {plan.audit.get('verdict')} "
              f"({len(plan.audit.get('findings', []))} findings)")
    return 0


def cmd_selftest(_args) -> int:
    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    # validator: const / required / enum / pattern / nested / type-list
    schema = {
        "type": "object",
        "required": ["schema", "tasks"],
        "properties": {
            "schema": {"const": "planning/x@1"},
            "tasks": {"type": "array", "minItems": 1,
                      "items": {"type": "object", "required": ["id"],
                                "properties": {"id": {"type": "string", "pattern": "^T[0-9]{2}$"}}}},
            "flag": {"type": ["string", "null"]},
        },
    }
    check("const ok", validate_against({"schema": "planning/x@1", "tasks": [{"id": "T01"}]}, schema) == [])
    check("const bad", validate_against({"schema": "planning/y@1", "tasks": [{"id": "T01"}]}, schema) != [])
    check("required bad", validate_against({"schema": "planning/x@1"}, schema) != [])
    check("pattern bad", validate_against({"schema": "planning/x@1", "tasks": [{"id": "T1"}]}, schema) != [])
    check("type-list null ok", validate_against({"schema": "planning/x@1", "tasks": [{"id": "T01"}], "flag": None}, schema) == [])
    check("minItems bad", validate_against({"schema": "planning/x@1", "tasks": []}, schema) != [])

    # cycle detection
    check("cycle found", has_cycle(["T01", "T02", "T03"], [
        {"from": "T01", "to": "T02"}, {"from": "T02", "to": "T03"}, {"from": "T03", "to": "T01"},
    ]) is not None)
    check("no cycle", has_cycle(["T01", "T02"], [{"from": "T01", "to": "T02"}]) is None)

    # longest path
    check("longest path", longest_path_hops(
        ["T01", "T02", "T03", "T04"],
        [{"from": "T01", "to": "T02"}, {"from": "T01", "to": "T03"}, {"from": "T03", "to": "T04"}],
    ) == 3)

    # ownership overlap helper via reachability
    reach = reachability(["T01", "T02"], [{"from": "T01", "to": "T02"}])
    check("reach", "T02" in reach["T01"] and "T01" not in reach["T02"])

    if failures:
        print("selftest FAILED: " + ", ".join(failures))
        return 1
    print("selftest OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="plan-check", description=__doc__)
    parser.add_argument("--schemas-dir", default=str(DEFAULT_SCHEMAS_DIR),
                        help="directory holding planning/*.schema.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate"); p.add_argument("file")
    p = sub.add_parser("lint"); p.add_argument("plan_dir")
    p.add_argument("--fail-on", choices=["BLOCKER", "MAJOR", "MINOR"], default="BLOCKER")
    p = sub.add_parser("report"); p.add_argument("plan_dir")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    # schemas-dir must be parsed before the subcommand handler uses defaults
    return {
        "validate": cmd_validate,
        "lint": cmd_lint,
        "report": cmd_report,
        "selftest": cmd_selftest,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
