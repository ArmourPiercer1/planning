# Audit Run — Independent Plan Audit (plan-auditor)

You are a FRESH auditor with no prior context about this plan and no access
to the planning conversation. Audit the plan in `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-04-audit-async\candidate\out` following
`D:\AI_Coworking\skill-build\planning\.agents\skills/plan-auditor/SKILL.md` and the shared vocabulary in
`D:\AI_Coworking\skill-build\planning\.agents\references\glossary.md`.

**Inputs allowed: the plan directory, that one skill, the glossary. Nothing
else.** You must not read the repo fixture, the task prompt, or any
evaluation file.

## Procedure

1. **Deterministic layer.** Run:

   ```powershell
   $env:UV_CACHE_DIR = "D:\AI_Coworking\skill-build\planning\.cache\uv"
   uv run --no-project python D:\AI_Coworking\skill-build\planning\.agents\scripts\plan-check.py lint D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-04-audit-async\candidate\out
   ```

   Record its exit code and finding count.
2. **Semantic layer.** Perform the skill's semantic checklist against the
   artifacts; each finding needs a quoted evidence location and a suggested fix.
3. **Write `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-04-audit-async\candidate\out/audit.json`** (schema `planning/audit@1`):
   - `verdict`: PASS iff zero BLOCKER findings (deterministic + semantic);
   - `findings[]`: severity BLOCKER/MAJOR/MINOR, check name, evidence,
     suggested_fix;
   - `deterministic`: the lint exit code and finding count from step 1;
   - `checks_performed`: the list of semantic checks you performed;
   - `auditor`: `path: "fresh_subagent"`, `planner_conversation_isolated: true`;
   - `revision_round`: 2.

Do NOT modify any plan artifact. Do NOT re-plan. Final message: `AUDIT DONE`
plus the verdict.
