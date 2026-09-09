# Planning Run — Candidate (Planning Compiler Skills)

You are the planning agent for one case in a planning-quality evaluation.

## Your input (read ONLY these, plus what this prompt names)

- Task: `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\ablation-full-minus-integration\task.md`
- Repo fixture: `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\ablation-full-minus-integration\work\repo` — explore it to understand context closures.
- Planning skills (the pipeline you must follow): `D:\AI_Coworking\skill-build\planning\.agents\skills/long-task-planning/SKILL.md`
  and the stage skills it references under `D:\AI_Coworking\skill-build\planning\.agents\skills/` (one SKILL.md each),
  plus `D:\AI_Coworking\skill-build\planning\.agents\references\glossary.md` for shared vocabulary.
- Deterministic gate: `D:\AI_Coworking\skill-build\planning\.agents\scripts\plan-check.py`

## Protocol

1. Read the orchestrator skill and follow its fixed pipeline.
2. Run the planning stages, writing artifacts to `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\ablation-full-minus-integration\out` with the standard
   file names (stage-contract.json, candidate-tasks.json, dag.json,
   integration-plan.json, tasks/T*.json, risk-estimates.json, run-manifest.json).
3. After each stage, run the deterministic gate and fix findings before
   proceeding:

   ```powershell
   $env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"
   uv run --no-project python D:\AI_Coworking\skill-build\planning\.agents\scripts\plan-check.py validate <artifact>
   ```

4. After the risk stage, run the full lint and resolve all BLOCKER findings:

   ```powershell
   uv run --no-project python D:\AI_Coworking\skill-build\planning\.agents\scripts\plan-check.py lint D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\ablation-full-minus-integration\out
   ```

5. Do NOT run the independent audit stage and do NOT write audit.json — a
   separate, isolated auditor reviews your artifacts after you finish.
6. Telemetry (mandatory): every time you read a file, append one JSON line to
   `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\ablation-full-minus-integration\telemetry.jsonl`: `{"ts":"<iso>","op":"read","path":"<path>"}`.
   Every time you write or modify a file, append `{"ts":"...","op":"write","path":"..."}`.
7. Budget discipline: read at most a handful of repo files per stage — enough
   to judge context closures honestly. Plan quality is judged on the plan
   structure, not on how much you explored.
8. Hard rules:
   - Work only inside `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\ablation-full-minus-integration\work\repo` (plus the skill files, the glossary, and the gate script above).
   - Never read evaluation files (case definitions, expected constraints, trap
     documentation). They are not part of your input set; if you encounter a
     directory named `fixtures`, `expected`, or `reports`, do not open it.
   - The plan must be internally consistent and honest: files that do not exist
     yet are marked `(new)` in `required_context.files`.

## Stage override (ablation: integration-planner removed)

Skip the integration-planning stage: no seam census, no integration tasks, no
E2E gates, no owns_fixes_for. Plan only the implementation (leaf) tasks. Do
NOT write `integration-plan.json` at all — the missing artifact is the
expected ablation outcome; do not create a stub.

## Finish

When the lint is clean (or only MINOR findings remain, listed in
run-manifest.json), write `DONE` plus a 3-line summary (task count, parallel
groups, critical path) as your final message.
