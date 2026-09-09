---
name: repo-context-snapshot
description: Stage 0 of the planning pipeline. Run the bounded repo scan script to produce a machine-readable context snapshot covering file/layer map, one-hop import graph, known shared files, known seams across layers, and TODO/FIXME census. Every subsequent stage reads this artifact instead of re-scanning the repo; the auditor grounds plan claims against it. Use only as the first step of /long-task-planning, or standalone when a bounded repo picture is needed. NOT a full-codebase index; scope it to the Stage territory.
---

# repo-context-snapshot

Ground every later plan claim in a bounded, script-generated picture of the
repo. This stage runs a deterministic scan — not a manual "repo notes"
gathering — and emits a JSON artifact every other stage reads instead of
re-scanning. Vocabulary: `../../references/glossary.md`.

## Trigger

- Use: pipeline stage 0, before anything else in the long-task-planning
  pipeline; or standalone when a bounded repo scan is needed.
- Do NOT use: as a replacement for reading one specific file the user names;
  to index the entire codebase without a Stage boundary (scope the scan to
  the territory the plan actually touches).

## Inputs

- `--repo` — path to the repository root.
- `--scope` — one or more prefix directories the Stage territory covers
  (e.g. `app/api/`, `app/services/`). Multiple scopes can be given.
- Optional: `--max-files N` (default 150) to cap the scan; the script will
  abort if the scope exceeds the cap, forcing a tighter scope.
- `<plan-dir>/input.md` — if it exists, the verbatim user task to help judge
  the scope (not parsed mechanically).

## Procedure

1. **Decide the scan scope.** From the user task (input.md), determine which
   directories the Stage territory covers. At minimum, include directories
   that contain files the plan will read, modify, or where new files land.
   If the task touches the whole service, scope the `app/` and `tests/`
   directories. A scope that is too narrow means later stages will miss
   imports or shared files — a scope that is too wide wastes budget and
   dilutes the snapshot.

2. **Run the scan script.** Execute:
   ```
   uv run --no-project python ../../scripts/repo-snapshot.py \
     --repo <repo-root> --out <plan-dir>/repo-context-snapshot.json \
     --scope <prefix1> --scope <prefix2> …
   ```
   (Set `UV_CACHE_DIR` to a writable path if the sandbox denies the default.)
   The script is stdlib Python: no install, no venv. It:
   - enumerates files under each scope (git-indexed or plain filesystem,
     excluding `SKIP_DIRS` like `.git`, `node_modules`, `__pycache__`);
   - resolves one-hop imports (including relative imports) to in-scope
     repo-relative paths, recording top-level exports where parseable;
   - applies layer rules using path segments + stem to assign a
     responsibility layer (`ui / store / api / service / runtime /
     persistence / lifecycle / e2e / tooling / docs`);
   - identifies `known_shared_files` (imported by ≥ 2 distinct files),
     `known_seams` (shared files imported across ≥ 2 layers);
   - censuses TODO/FIXME/XXX/HACK markers (capped at 50);
   - computes `unknown_areas` — top-level directories under scope with no
     matching file (only when scopes are non-empty; a whole-repo scan has
     none).

3. **Inspect the output.** Check that:
   - The number of scanned files is reasonable (not 0, not hitting the cap).
   - Key directories the plan will touch appear in the file list.
   - `unknown_areas` is empty or explains genuinely missing territory.
   - `known_shared_files` and `known_seams` reflect real cross-cutting points.
   If the scope misses territory, widen it and re-run.

4. **Gate.** Run `plan-check.py validate` — the artifact is part of the
   completeness check (all later stages require its presence). The lint
   checks whether the snapshot references a plausible git revision and has
   the expected structure.

## Heuristics

- **Scope to the Stage, not the repo.** If the Stage only touches the API
  layer, scope `app/api/` and its imports — don't scan a 50K-line
  monolith. A tight snapshot is more useful to the decomposer and auditor.
- **Wider is safer than narrower** when in doubt: the decomposer uses the
  snapshot as its inventory, and a file not in it cannot be in a context
  closure (`CONTEXT_FILE_NOT_IN_SNAPSHOT`). A missing import means the
  auditor can't flag a hidden dependency.
- **The script is the authority.** Do not manually edit the output JSON.
  If a file should be in scope, widen the `--scope` and re-run. If it
  should be excluded, check the SKIP_DIRS logic. The auditor trusts the
  script's output.
- **A snapshot without a revision is a snapshot without grounding.** Use the
  `--repo` option with a git repository — the script records `HEAD`
  automatically. For non-git repos, the revision field will be
  `nogit:<sha16>` — note this limitation.

## Output

`<plan-dir>/repo-context-snapshot.json` (schema `planning/repo-context-snapshot@1`).
Contains: `scan_root`, `repo_revision`, `scopes`, `files[]` (each with
`path`, `layer`, `imports[]`, `exports[]`), `known_shared_files[]`,
`known_seams[]`, `known_todos[]`, `unknown_areas[]`.

## Failure & Escalation

- The scope hits the `--max-files` cap → narrow the scope or raise the cap.
  Report which directories contribute the most files.
- `unknown_areas` is non-empty and large → the plan depends on territory
  the scan didn't reach. Either widen the scope or note the gap explicitly;
  the auditor will flag claims about unknown areas as ungrounded.
- The script fails on a parse error in one file → skip that file and
  continue; record a note in the snapshot's `notes` field.
- No files found under any scope → the scope paths are wrong relative to
  the repo root; fix the paths and re-run.

## Examples

**Good.** Stage adds report jobs to a FastAPI service. Scopes:
`--scope app/api/ --scope app/services/ --scope app/db/ --scope tests/`.
Output: 12 files, 2 known shared files (`app/api/deps.py`, `app/db/base.py`),
0 known seams, 3 TODOs found. Decomposer uses it as the inventory; auditor
cross-checks every context file against it.

**Anti-pattern.** Scope set to the whole repo root, 500 files scanned, the
snapshot is mostly irrelevant boilerplate, and the decomposer can't tell
which 12 files matter. Or scope too narrow — only `app/api/` — so the
decomposer's closure misses the imports that lead to `app/services/`, and
the auditor can't flag the hidden dependency.
