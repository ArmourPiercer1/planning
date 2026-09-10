# HANDOFF — p5-v1.1-r1 (Monthly PDF Export)

**Governor action:** EXECUTE
**Audit verdict:** PASS (isolated subagent, revision_round 3; F01-F04 resolved, F05/F06 deferred OPTIONAL)
**Final lint:** exit 0 — 0 BLOCKERs, 0 MAJORs, 17 MINORs (VAGUE_ACCEPTANCE style)
**Delivery profile:** alpha
**Repo:** evals/probes/repos/p5-report-export (rev 790b314)

## Execution Plan Summary

6 tasks, 3 parallel groups:

| Group | Tasks | Parallel |
|-------|-------|----------|
| 1 | T01 (job store + worker), T02 (PDF export + i18n + shim), T03 (API endpoints) | all three in parallel |
| 2 | T04 (contract consistency), T05 (seam integration) | in parallel |
| 3 | T06 (E2E closure + final acceptance) | alone |

Critical path: T01 → T04 → T06 (any leaf → integration → E2E)

## Task List

| ID | Objective | Depends on |
|----|-----------|------------|
| T01 | In-process job store + background worker (pending→running→done/failed) | — (frozen C2) |
| T02 | PDF export service + i18n EN/DE + vendored pdflib_shim | — |
| T03 | Three API endpoints (POST export-pdf, GET job, GET download) | — (frozen C1) |
| T04 | Contract consistency check (C1/C2/C3 vs implementations, read-only) | T01, T02, T03 |
| T05 | Seam integration (S1: API↔JobStore, S2: Worker↔PDF) | T01, T02, T03, T04 |
| T06 | E2E gates E1–E5 + acceptance A1–A5 | T04, T05 |

## Frozen Contracts

- **C1** (state): JobStore interface — create/get, state machine pending→running→done|failed
- **C2** (service): PdfExportService.export_pdf(customer_id, report_id, lang) → bytes
- **C3** (api): POST /reports/{id}/export-pdf → 202, GET /jobs/{id} → 200, GET /jobs/{id}/download → 200/409/404

## Seams

- **S1**: API ↔ JobStore (T03, T01) — contracts C1, C3
- **S2**: Worker ↔ PdfExportService (T01, T02) — contracts C1, C2

## E2E Gates

- E1: Happy path (POST → poll → download PDF)
- E2: Unknown report → 404
- E3: Invalid lang → 400
- E4: Download before done → 409
- E5: Job failure → status failed with error

## Acceptance Criteria

- A1: POST returns 202 with job_id
- A2: GET /jobs/{id} reflects state transitions
- A3: Download returns valid PDF bytes when done
- A4: PDF labels in requested language (EN/DE)
- A5: Existing CSV export tests remain green

## Out of Scope

- Email delivery, report editing/creation, archive/retention, CSV refactor, DB changes

## Audit Findings (isolated subagent, rev 3 — all resolved)

| ID | Severity | Check | Routing | Status |
|----|----------|-------|---------|--------|
| F01 | MAJOR | schema_invalid | POST_STAGE | **RESOLVED** — stage-contract re-emitted as @3 with filled horizons |
| F02 | MINOR | schema_invalid | OPTIONAL | **RESOLVED** — run-manifest rewritten to run-manifest@1 schema |
| F03 | MINOR | late_contract_freeze | OPTIONAL | **RESOLVED** — DA-PDF-PER-REPORT text matches C2 |
| F04 | MINOR | hidden_dependency | OPTIONAL | **RESOLVED** — C2 inlined in T01 frozen_contracts |
| F05 | MINOR | nondeterministic_acceptance | OPTIONAL | Deferred — A4 checkable via T02's i18n module + AT06 |
| F06 | MINOR | deterministic_lint | OPTIONAL | Deferred — 17 style-only VAGUE_ACCEPTANCE findings |

## Warnings Carried into Execution

1. **F01 (POST_STAGE):** Re-emit stage-contract as @3 when the @3 schema is deployed; fill horizons.detailed_stage.tasks and stage_boundary.stop_after
2. **F03 (OPTIONAL):** Edit DA-PDF-PER-REPORT to match C2 (single report per export)
3. **F04 (OPTIONAL):** Add C2 to T01's frozen_contracts
4. **17 VAGUE_ACCEPTANCE (style):** Acceptance description fields lack inline pytest markers; evidence fields are sufficient

## Artifacts

All in `evals/probes/runs/p5-v1.1-r1/plan/`:
- `input.md` — verbatim task
- `repo-context-snapshot.json` — stage 0
- `stage-contract.json` — stage 1
- `candidate-tasks.json` — stage 2
- `dag.json` — stage 3
- `integration-plan.json` — stage 4
- `tasks/T01.json` … `tasks/T06.json` — stage 5
- `risk-estimates.json` — stage 6
- `audit.json` — stage 7 (isolated subagent, rev 2)
- `governor-decision.json` — stage 8
- `run-manifest.json` — pipeline telemetry
