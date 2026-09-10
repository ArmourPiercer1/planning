#!/usr/bin/env python3
"""repo-snapshot — bounded, reproducible repo scan for planning + auditor grounding.

Stage 0 of the long-task-planning pipeline. Produces
`repo-context-snapshot.json` (schema planning/repo-context-snapshot@1): a
one-hop dependency picture of the in-scope repo files, enough for the
planner to decompose against reality and for the independent auditor to
verify plan claims WITHOUT re-scanning the whole repo.

V1 supports **Python repositories only** (stdlib AST). Non-Python repos
are not supported — see `SNAPSHOT_UNSUPPORTED_OR_EMPTY`.

Zero-dependency (stdlib only), deterministic for a given repo revision.
Usage:
    uv run --no-project python repo-snapshot.py --repo <repo-dir> --out <file>
        [--scope <prefix> ...] [--max-files N]

Scope prefixes are repo-relative posix paths (e.g. "app", "profiles").
Without --scope the whole repo is the scan boundary. Unscanned top-level
areas are recorded in `unknown_areas` — never silently absent.

One-hop expansion: seed files are collected from explicit --scope prefixes,
then their repo-local Python imports are resolved and included even if the
target lies outside the scope. The second hop is NOT followed. Expansion
entries are recorded in `dependency_expansions`.

Fail-fast: if the total file count (seed + expansion) exceeds --max-files,
the script exits non-zero with `SNAPSHOT_SCOPE_TOO_LARGE` — it never
produces a silently truncated snapshot.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".cache",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".plans", ".idea",
    ".tox", "uv", "site-packages",
}
TODO_RE = ("TODO", "FIXME", "XXX", "HACK")
DEBT_RE = ("refactor", "debt", "legacy", "tech debt", "deprecated")

LAYER_RULES = [
    (["api", "routes", "route", "http", "rest", "endpoints"], "api"),
    (["db", "models", "model", "store", "repo", "persistence", "migrations"], "persistence"),
    (["runtime", "worker", "engine", "core", "state", "exec"], "runtime"),
    (["lifecycle"], "lifecycle"),
    (["ui", "templates", "static", "frontend", "views", "web"], "ui"),
    (["scripts", "tooling", "tools", "cli"], "tooling"),
    (["service", "services", "logic", "domain"], "service"),
]


def _git_head(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _nogit_revision(repo: Path, files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in sorted(files):
        rel = f.relative_to(repo).as_posix()
        try:
            h.update(f"{rel}:{int(f.stat().st_mtime)}".encode())
        except OSError:
            h.update(rel.encode())
    return "nogit:" + h.hexdigest()[:16]


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./").strip("/")


def _in_scope(rel: str, scopes: list[str]) -> bool:
    if not scopes:
        return True
    for s in scopes:
        if rel == s or rel.startswith(s + "/"):
            return True
    return False


def _layer_of(rel: str) -> str:
    segs = [s.lower() for s in rel.split("/")[:-1]]
    base = rel.rsplit("/", 1)[-1].lower()
    if base.startswith("test_") or base == "conftest.py" or "tests" in segs or "test" in segs:
        return "e2e"
    if base in ("main.py", "app.py", "server.py"):
        return "lifecycle"
    all_parts = segs + [base.rsplit(".", 1)[0]]
    for needles, layer in LAYER_RULES:
        if any(n in all_parts for n in needles):
            return layer
    return "service"


def _extract_imports(src: Path) -> list[str]:
    """Return raw module names imported by one .py file."""
    try:
        tree = ast.parse(src.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return []
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                modules.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                pkg = src.parent.as_posix()
                up = node.level - 1
                parts = pkg.split("/")
                if up:
                    parts = parts[: len(parts) - up] if up < len(parts) else []
                base = "/".join(parts)
                mod = (base + "." + node.module) if node.module else base
            else:
                mod = node.module or ""
            if mod:
                modules.append(mod)
    return sorted(set(modules))


def _extract_full(src: Path) -> tuple[list[str], list[str], str]:
    """Return (imports_raw_modules, exports, role) for one file."""
    modules = _extract_imports(src)
    try:
        tree = ast.parse(src.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return modules, [], f"module (unparseable): {src.stem}"
    exports = sorted(
        n.name for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    doc = ast.get_docstring(tree)
    role = (doc.strip().splitlines()[0][:120]) if doc else f"module: {src.stem}"
    return modules, exports, role


def _resolve_module(mod: str, bases: list[Path], known: set[str]) -> str | None:
    for base in bases:
        rel = Path(mod.replace(".", "/"))
        for cand in (base / rel.with_suffix(".py"), base / rel / "__init__.py"):
            try:
                r = cand.relative_to(repo_root_global).as_posix()
            except ValueError:
                continue
            if r in known and cand.is_file():
                return r
    return None


repo_root_global: Path = Path(".")


def _has_any_py(repo: Path) -> bool:
    """Check if repo contains any .py files at all (bounded walk)."""
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(".py"):
                return True
    return False


def main(argv: list[str] | None = None) -> int:
    global repo_root_global
    ap = argparse.ArgumentParser(prog="repo-snapshot", description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scope", action="append", default=[],
                    help="repo-relative prefix to scan (repeatable); default: whole repo")
    ap.add_argument("--max-files", type=int, default=150)
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(json.dumps({"error": f"not a directory: {repo}"}))
        return 2
    repo_root_global = repo
    scopes = [_norm(s) for s in args.scope if _norm(s)]

    # P1-1: Python-only check
    if not _has_any_py(repo):
        err = {"error": "SNAPSHOT_UNSUPPORTED_OR_EMPTY",
               "detail": "No Python files found in the repository. V1 supports Python-only."}
        print(json.dumps(err, indent=2))
        return 3

    # Step 1: collect seed files from explicit scope
    seed_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            p = Path(dirpath) / fn
            rel = p.relative_to(repo).as_posix()
            if not _in_scope(rel, scopes):
                continue
            seed_files.append(p)

    # Step 2: P0-2 — one-hop expansion: resolve imports of seed files
    # Build initial known set from seed, then expand to one-hop targets
    known = {p.relative_to(repo).as_posix() for p in seed_files}
    expanded: set[str] = set()
    bases = [repo] + [repo / s for s in scopes if s]
    for p in seed_files:
        rel = p.relative_to(repo).as_posix()
        for mod in _extract_imports(p):
            # Try to resolve this module to an existing file
            rel_path = Path(mod.replace(".", "/"))
            for cand in (repo / rel_path.with_suffix(".py"), repo / rel_path / "__init__.py"):
                try:
                    r = cand.relative_to(repo).as_posix()
                except ValueError:
                    continue
                if r != rel and r not in expanded and r not in known and cand.is_file():
                    expanded.add(r)
                    known.add(r)
                    break  # one match is enough for this module

    # Build final collected list: seed + expansions
    collected = list(seed_files)
    for exp_rel in sorted(expanded):
        exp_path = repo / exp_rel
        if exp_path.is_file():
            collected.append(exp_path)

    # P0-1: fail-fast if total exceeds cap
    if len(collected) > args.max_files:
        err = {
            "error": "SNAPSHOT_SCOPE_TOO_LARGE",
            "matched_files": len(collected),
            "max_files": args.max_files,
            "detail": "Widen --max-files or narrow --scope. Snapshot not produced."
        }
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 1

    revision = _git_head(repo) or _nogit_revision(repo, collected)

    file_entries = []
    importers: dict[str, set[str]] = {}
    todos: list[str] = []
    for p in sorted(collected):
        rel = p.relative_to(repo).as_posix()
        modules, exports, role = _extract_full(p)
        resolved = []
        for m in modules:
            r = _resolve_module(m, bases, known)
            if r and r != rel:
                resolved.append(r)
        resolved = sorted(set(resolved))
        for r in resolved:
            importers.setdefault(r, set()).add(rel)
        file_entries.append({
            "path": rel,
            "layer": _layer_of(rel),
            "role": role,
            "imports": resolved,
            "exports": exports,
        })
        # TODO / tech-debt temptation census (bounded)
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if any(t in s.upper() for t in TODO_RE) and len(todos) < 50:
                todos.append(f"{rel}:{i}: {s[:160]}")

    shared = sorted(r for r, inc in importers.items() if len(inc) >= 2)
    layer_of = {e["path"]: e["layer"] for e in file_entries}
    seams = []
    for r in shared:
        layers = sorted({layer_of[i] for i in importers[r] if i in layer_of} - {layer_of.get(r)})
        if len(layers) >= 2:
            seams.append(f"{r} (imported across layers: {', '.join(layers)})")

    test_entries = sorted(e["path"] for e in file_entries if layer_of[e["path"]] == "e2e")
    debt = [t for t in todos if any(k in t.lower() for k in DEBT_RE)]

    # unknown areas: top-level entries not covered by any scope prefix
    # (empty scope = whole repo scanned = nothing unknown)
    unknown = []
    if scopes and repo.exists():
        for entry in sorted(repo.iterdir(), key=lambda e: e.name):
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            name = entry.name.rstrip("/")
            if not any(name == s or name.startswith(s.rstrip("/") + "/") for s in scopes):
                unknown.append(entry.name + ("/" if entry.is_dir() else ""))
            if len(unknown) >= 30:
                break

    snapshot = {
        "schema": "planning/repo-context-snapshot@1",
        "repo_revision": revision,
        "scope_root": ".",
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": file_entries,
        "known_test_entrypoints": test_entries,
        "known_shared_files": shared,
        "known_todos": todos,
        "known_tech_debt": debt,
        "known_seams": seams,
        "scan_boundary": scopes or ["."],
        "dependency_expansions": sorted(expanded),
        "unknown_areas": unknown,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(out), "repo_revision": revision, "files": len(file_entries),
        "shared": len(shared), "todos": len(todos),
        "dependency_expansions": len(expanded),
        "unknown_areas": len(unknown),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
