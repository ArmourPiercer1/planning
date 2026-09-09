/**
 * workflow_template.js — skeleton for the host to render/run per eval invocation.
 *
 * Placeholders: {{RUN_ID}}, {{SPECS_JSON}}, {{PLANNING_TIMEOUT_HINT}}
 * SPECS_JSON = [{case_id, variant, run_dir, prompt_file, needs_audit, executor}]
 *
 * The host renders this template (filling placeholders) and passes it to the
 * workflow tool. It is a skeleton, not a committed executable artifact: the
 * agent() prompts point at per-run prompt files so that every subagent sees
 * exactly the content of ORCHESTRATION.md's invariants — no case metadata.
 *
 * Phases:
 *   1. planning     — one subagent per spec (structured or prose)
 *   2. audit        — fresh subagent per audited spec; FAIL => one revision
 *                     subagent + re-audit (max 2 audit rounds)
 *   3. execution    — fresh executor subagent for specs flagged executor=true
 *
 * Wall time is measured in-script (Date.now around each agent) and written to
 * <run_dir>/timing.json by the host after the workflow settles (the workflow
 * returns the timings; the host merges them before `score`).
 */

const SPECS = {{SPECS_JSON}};
const RUN_ID = "{{RUN_ID}}";

function planningPrompt(s) {
  return (
    `You are a planning subagent for an evaluation run. ` +
    `Your ENTIRE task specification is the file ${s.prompt_file}. ` +
    `Read it first and follow it to the letter, including the telemetry protocol ` +
    `and the hard rules about which paths you may read. ` +
    `Do not read any other evaluation files. Finish with the marker the prompt defines.`
  );
}

function auditPrompt(s, round) {
  return (
    `You are a fresh, independent plan auditor with no prior context. ` +
    `Your ENTIRE task specification is the file ${s.run_dir.replace(/\\/g, '/')}__audit_prompt_r${round}.md ` +
    `(rendered by the host from runners/prompts/audit.md). Read it and follow it; ` +
    `write audit.json with revision_round ${round}. Inputs are limited to the plan ` +
    `directory, the plan-auditor skill, and the glossary.`
  );
}

function revisionPrompt(s, auditJson) {
  return (
    `You are the planner from the original run for ${s.case_id}. An independent ` +
    `auditor rejected the plan. Read ${s.prompt_file} again for the original spec, ` +
    `then read ${s.run_dir.replace(/\\/g, '/')}out/audit.json and fix ONLY the ` +
    `BLOCKER and MAJOR findings in the artifacts under ${s.run_dir.replace(/\\/g, '/')}out. ` +
    `Re-run the deterministic gate (plan-check lint) until clean. Telemetry protocol still applies.`
  );
}

async function planWithAudit(s) {
  const t0 = Date.now();
  const final = await agent(planningPrompt(s), { label: `plan:${s.case_id}:${s.variant}` });
  let verdict = "no-audit";
  if (s.needs_audit) {
    for (let round = 1; round <= 2; round++) {
      await agent(auditPrompt(s, round), { label: `audit${round}:${s.case_id}:${s.variant}` });
      const aj = `READ_FILE:${s.run_dir}/out/audit.json`;
      const audit = await agent(
        `Read the file ${s.run_dir.replace(/\\/g, '/')}out/audit.json and return ONLY its "verdict" field value (PASS or FAIL) plus, if FAIL, the list of BLOCKER/MAJOR finding codes as a JSON array.`,
        { label: `audit-read:${s.case_id}:r${round}`, phase: "audit" }
      );
      const m = /"(PASS|FAIL)"/.exec(String(audit));
      verdict = m ? m[1] : "FAIL";
      if (verdict === "PASS") break;
      if (round < 2) {
        await agent(revisionPrompt(s, aj), { label: `revise:${s.case_id}:${s.variant}` });
      }
    }
  }
  return { case_id: s.case_id, variant: s.variant, planning: String(final).slice(0, 400),
           audit_verdict: verdict, wall_time_seconds: (Date.now() - t0) / 1000 };
}

phase("planning");
const specsToPlan = SPECS.filter((s) => !s.executor);
const planResults = await pipeline(specsToPlan, (s) => planWithAudit(s));

phase("execution");
const execResults = await pipeline(SPECS.filter((s) => s.executor), async (s) => {
  const t0 = Date.now();
  const out = await agent(
    `You are a fresh execution subagent. Your ENTIRE task specification is the file ` +
    `${s.run_dir.replace(/\\/g, '/')}__executor_prompt.md (rendered by the host from ` +
    `runners/prompts/executor.md). Read it and follow it to the letter. Execute the plan ` +
    `in ${s.run_dir.replace(/\\/g, '/')}out against ${s.run_dir.replace(/\\/g, '/')}work/repo. ` +
    `Telemetry protocol applies. Finish with EXEC DONE.`,
    { label: `exec:${s.case_id}:${s.variant}` }
  );
  return { case_id: s.case_id, variant: s.variant, exec: String(out).slice(0, 400),
           wall_time_seconds: (Date.now() - t0) / 1000 };
});

return { run_id: RUN_ID, planning: planResults.filter(Boolean), execution: execResults.filter(Boolean) };
