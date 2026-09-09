# Audit Run — Independent Plan Audit (plan-auditor)

You are a FRESH auditor with no prior context about this plan and no access
to the planning conversation. Audit the plan in `{plan_out}` following
`{skills_dir}/plan-auditor/SKILL.md` and the shared vocabulary in
`{glossary}`.

**Inputs allowed: the plan directory (including repo-context-snapshot.json), that
one skill, the glossary. You may also open snapshot-listed files for read-only
spot checks — never walk the whole repo. Nothing else.** You must not read
the task prompt or any evaluation file.

## Procedure

1. **Deterministic layer.** Run:

   ```powershell
   $env:UV_CACHE_DIR = "{uv_cache}"
   uv run --no-project python {plan_check} lint {plan_out}
   ```

   Record its exit code and finding count.
2. **Semantic layer.** Perform the skill's semantic checklist against the
   artifacts; each finding needs a quoted evidence location and a suggested fix.
3. **Grounding pass.** Load `repo-context-snapshot.json`. Verify the plan's
   repo-facing claims against it. Record `grounding`: `snapshot_ref`,
   `repo_revision`, `files_verified`, `notes`.
4. **Write `{plan_out}/audit.json`** (schema `planning/audit@2`):
   - `verdict`: PASS iff zero BLOCKER findings (deterministic + semantic);
   - `findings[]`: severity BLOCKER/MAJOR/MINOR, check name, evidence,
     suggested_fix;
   - `deterministic`: the lint exit code and finding count from step 1;
   - `checks_performed`: the list of semantic checks you performed;
   - `grounding`: `snapshot_ref`, `repo_revision`, `files_verified`, `notes`;
   - `auditor`: `path: "fresh_subagent"`, `planner_conversation_isolated: true`;
   - `revision_round`: {round}.

Do NOT modify any plan artifact. Do NOT re-plan. Final message: `AUDIT DONE`
plus the verdict.
