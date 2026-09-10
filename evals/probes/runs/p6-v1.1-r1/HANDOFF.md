# P6 v1.1 r1 — handoff (final, post stage-8 re-run)

**Probe:** P6 cross-drift (frozen C1 + additive C2 + new C3; product-ticket `last_notified_at` request)
**Repo:** `evals/probes/repos/p6-cross-drift/`
**Plan dir:** `evals/probes/runs/p6-v1.1-r1/plan/`
**Score:** `evals/probes/results/P6-v1.1-r1.json` → **PASS, 1.0 (4/4 checks)** — re-scored after the stage-8 re-run
**Governor:** **EXECUTE** (stage-8 re-run on the superseding round-2 audit; 0 blockers, 0 spikes; F01/F02/F03 + Q1 deferred OPTIONAL)
**Final lint:** 0 BLOCKER / 0 MAJOR / 0 MINOR (exit 0); all artifacts incl. run-manifest validate against their schemas

## Stage trace (run-manifest.json is the append-only record, now in run-manifest@1 shape)

| # | Skill | Artifact | Gate |
|---|---|---|---|
| 0 | repo-context-snapshot | repo-context-snapshot.json | G0 exit 0 |
| 1 | stage-contract | stage-contract.json | G1 exit 0 (retry: frozen-id pattern A-1/DA-1) |
| 2 | context-decomposer | candidate-tasks.json (T01, T02) | G2 exit 0 |
| 3 | dependency-dag | dag.json | G3 exit 0 |
| 4 | integration-planner | integration-plan.json + amended dag.json (T03, G1, E1–E3) | G4 exit 0 |
| 5 | task-packager | tasks/T01–T03.json (+ inline-frozen-contracts.py) | G5 exit 0 |
| 6 | plan-risk-estimator | risk-estimates.json + final risk blocks | G6 exit 0, lint 0/0/0 |
| 7 | plan-auditor | audit.json — round 1 (SUPERSEDED: in-conversation late pass; invalid isolation self-certification — does not count as an accepted full audit) | G7 exit 0 |
| 7 | plan-auditor (isolated re-audit, revision_round 2) | audit.json — REPLACED by parent-dispatched fresh-subagent audit: PASS, 0 BLOCKER / 0 MAJOR / 3 MINOR (all OPTIONAL) | G7b exit 0 |
| 8 | planning-governor | governor-decision.json — round 1 (SUPERSEDED: issued on round-1 audit) | G8 exit 0 |
| 8 | planning-governor (RE-RUN) | governor-decision.json on round-2 audit: **EXECUTE** | G8b exit 0, final lint 0/0/0 |

## Key decisions

- **C1 frozen byte-identical** to stage 1 (round-2 auditor: RAW byte-identity incl. em-dash, identical unfreeze_rule + logical_owner) — the frozen API shape is untouched; the frozen stage-1 suite is the canary (A4).
- **C2 additive** (`webhook_url?: string` inserted after `tag?: string`, order preserved) per its unfreeze rule, proposed in writing in the contract spec — round-2 auditor confirmed pure additive.
- **`last_notified_at` NOT absorbed**: out_of_scope with rule-based reason + non-blocking open question **Q1 (owner: user/product sign-off)**; C1's unfreeze rule (contract-change request + sign-off) is the only path; conditional forecast stage pre-declared in horizons.forecast. Round-2 core judgment: **NO SILENT DRIFT** on any frozen stage-1 item (stage-1 out-of-scope carried forward too).
- **C3 new + frozen**: exactly-one/zero dispatch, payload shape, no-escape failure boundary (DA-2), dispatch never affects the HTTP result.
- All 7 inlined contract specs sha256-verified against the stage contract (round-2 auditor).

## Tasks

- **T01** registration closure — store + create_todo (api+persistence), C1/C2, owns `app/store.py`, `app/api.py`, `tests/test_registration.py (new)`
- **T02** dispatch closure — mark_done over the existing `WebhookDispatcher` (api+service), C2/C3, owns `app/api.py`, `tests/test_notifications.py (new)`; data dependency on T01 (webhook_url field), resolves the shared `app/api.py`
- **T03** e2e closure — merged `final_acceptance` + `contract_consistency`, owns `tests/test_e2e_notifications.py (new)`; gates E1 (round-trip + unknown-id 404), E2 (raising dispatcher + no-URL), E3 (frozen suite + C1 key set); `seam_integration` omitted with snapshot-grounded justification (no new production files)

## Audit (accepted round: 2 — isolated fresh subagent, parent-dispatched; verdict PASS)

- Deterministic layer re-run by the auditor: exit 0, 0 findings. Grounding: 7 files verified (api/store/webhooks/test_api + stage-1 pair + README), programmatic C1 raw byte-identity, C2 pure-additive check, sha256 of all 7 inlined specs.
- **F01 (MINOR, nondeterministic_acceptance, A1, OPTIONAL):** repeated mark_done is idempotent in the repo, so a repeat "succeeds"; C3's "(transition applied)" and A1.negative_case don't pin the repeat-done dispatch count — add the zero-dispatch assertion (+ optional C3 clause).
- **F02 (MINOR, hidden_dependency, T03, OPTIONAL):** T03's required_context.files under-declares `app/api.py`, `app/webhooks.py`, `app/store.py` needed by the E2 e2e imports — add them (read-only; owned_paths stays test-only).
- **F03 (MINOR, schema_invalid, OPTIONAL):** run-manifest.json failed its own run-manifest@1 schema (lint doesn't cover that file) — **fixed in the stage-8 re-run** as a record-keeping rewrite to @1 shape, history preserved.

## Governor (re-run, action EXECUTE)

- Step-4 routing: 0 EXECUTION_BLOCKER, 0 SPIKE_REQUIRED, only OPTIONAL findings → EXECUTE. TARGETED_PATCH not triggered (safe zone = all MAJOR + ≤2 findings; here 3 MINORs routed OPTIONAL), so no revision round, no re-audit dispatch.
- **Budget (parent ruling applied):** round-1 in-conversation audit = invalid isolation record, does not count; round-2 isolated audit = 1st accepted full audit (**1/2**); plan_revisions **0/3**; planning subagents **0/5**.
- F01/F02 deferred as execution warnings; F03 fixed as record-keeping; Q1 deferred (owner user).

## Warnings into execution

1. **F01** — add the re-done no-second-dispatch assertion in `tests/test_notifications.py` (and optionally the C3 clause).
2. **F02** — when executing T03, load `app/api.py`, `app/webhooks.py`, `app/store.py` (read-only) alongside the declared context.
3. **Schedule forecast:** p80 upper-bound sum ≈ 210 min vs stage_estimate 180 min, no parallelism — inside range coarseness (p50 sum ≈ 130 min); noted, not gated.
4. **Q1** is parked with the user; do not touch C1 or add `last_notified_at` during this stage.
