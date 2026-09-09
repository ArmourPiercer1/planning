---
name: plan-auditor
description: Independent review pass that gates a finished plan before execution. Runs the deterministic layer (plan-check lint) plus the semantic checklist — scope creep, insufficient non-goals, late contract freeze, hidden dependencies, fake serialization, ownership collision, oversized leaf, broad context loading, hidden integration work, nondeterministic acceptance, lack of local recoverability, append-only replan risk, communication overhead — and issues BLOCKER/MAJOR/MINOR findings. Must run from a path isolated from the planner conversation. Use as pipeline stage 7 of /long-task-planning, or for re-audit after targeted revision.
---

# plan-auditor

The auditor is a **different path**, not a second look by the same agent. An
audit that shares the planner's conversation inherits its blind spots — that
is the failure this stage exists to catch. Vocabulary:
`../../references/glossary.md`.

## Trigger

- Use: pipeline stage 7 (all artifacts exist); re-audit after any targeted
  revision round (increment `revision_round`).
- Do NOT use: mid-pipeline (artifacts are incomplete — the per-stage gates
  cover those); as a style review of the plan prose.

## Independence requirement (hard)

- Run as a **fresh subagent** (preferred) or fresh session that has **never
  seen the planning conversation**.
- Inputs allowed: the plan directory (artifacts only — including
  `repo-context-snapshot.json`), this skill, the glossary, and **read-only
  spot checks of files listed in the snapshot** (the grounding surface).
  Inputs forbidden: the planning chat log, the planner's reasoning, "the plan
  is basically fine, just check X", and free whole-repo scans (the snapshot is
  the bounded picture of the repo; re-scanning everything defeats the stage-0
  budget).
- Record in `audit.json auditor` which path was used and that
  `planner_conversation_isolated: true` — set it false only if the orchestrator
  explicitly downgraded isolation, and note the reason.

## Inputs

- The plan directory (all artifacts, `tasks/`, `checkpoints/` if any) — the
  complete input set, nothing else.
- `<plan-dir>/repo-context-snapshot.json` — the stage-0 repo picture (files,
  layers, one-hop imports, shared files, TODOs). This is the auditor's grounding
  surface: plan claims about the repo are checked against it, and spot checks
  may open only the files it lists.
- `plan-check.py` (the deterministic layer) and `../../references/glossary.md`
  (shared vocabulary for the findings).
- The audit round number (1, or N after targeted revisions).

## Procedure

1. **Deterministic layer.** Run
   `plan-check.py lint <plan-dir>` and record its exit code + finding count in
   `audit.json deterministic`. Every deterministic finding carries over as a
   finding with `check: deterministic_lint` (or its specific semantic check)
   and the same severity.
2. **Grounding pass (new in @2).** Load `repo-context-snapshot.json`.
   - Verify the plan's repo-facing claims against it: every context file
     that should exist, the import edges behind `hidden_dependency` and
     `late_contract_freeze` findings, the new-wiring facts behind any
     `omitted_kinds` entry, and the named non-goals (the in-repo TODO
     they cite is listed in `known_todos` — if it is not, the
     non-goal may be imagined).
   - Where a claim is checkable against a concrete file, do a read-only
     spot check of that snapshot-listed file. Never walk the whole repo.
   - If a spot check shows the repo moved under the plan (file content
     or structure no longer matches the snapshot), record a finding
     (`repo moved under the plan; re-run stage 0 and re-audit`) — the
     deterministic layer already emits `AUDIT_SNAPSHOT_MISMATCH` when the
     recorded revisions disagree.
   - Record `audit.json grounding`: `snapshot_ref`, `repo_revision`,
     `files_verified` (the snapshot-listed files you actually opened),
     `notes`. A missing grounding block is `AUDIT_NOT_GROUNDED` (MAJOR).
3. **Semantic layer** — for each check below, look for evidence in the
   artifacts and record a finding when present (each finding needs a quoted
   `evidence` location + the suggested fix):
   - `scope_creep` — in-scope items that are really B-class backlog or
     separate Stages; out-of-scope list missing the repo temptations;
   - `insufficient_non_goals` — non-goals that would not eliminate ambiguity
     (vague "no refactoring" without naming the tempting refactor);
   - `late_contract_freeze` — a contract consumed in parallel with its owner
     that is not frozen; parallelism assumed before the seam spec exists;
   - `hidden_dependency` — a package reads a file/output not declared in its
     required_context or allowed_dependencies (lint flags the snapshot-backed
     one-hop import cases; the auditor judges the rest — outputs, fixtures,
     data files);
   - `fake_serialization` — an edge whose reason does not survive the
     4-type test; a `fake_serialization_removed` list that is empty when the
     doc ordering clearly suggested edges;
   - `ownership_collision` — unordered tasks with overlapping owned paths
     (lint catches the prefix cases; the auditor catches directory-boundary
     judgment calls and fixture/test overlap);
   - `oversized_leaf` — XL without justification; a leaf that is actually a
     Phase (≥ 5 layers, or its objective enumerates sub-deliverables);
   - `broad_context_loading` — required_context much larger than the closure
     implies (lint flags size; the auditor judges necessity);
   - `hidden_integration_work` — a seam with no gate; an E2E scenario list
     with no failure scenarios; "integration happens in T03" style leaks;
     an `omitted_kinds` entry for `seam_integration` that the snapshot
     contradicts (a leaf creates new files in a directory that already
     contains another leaf's code — the new-wiring rule);
   - `nondeterministic_acceptance` — a criterion a third party could not
     judge PASS/FAIL from the text (lint flags phrase hits; the auditor
     confirms and catches phrase-free vagueness like "fast enough");
   - `lack_of_local_recoverability` — a leaf whose failure restarts the Stage
     (owns a path every other task needs, no checkpoint subgoals,
     integration task that can only run after *everything* when a subset
     would do);
   - `replan_only_by_append` — allowed_replan reduced to scope growth; plan
     structure with no defer/reduce/replace path visible;
   - `communication_overhead` — packages requiring the whole plan to be read;
     unnecessary reviewer/agent hops; checkpoint requirements that duplicate
     information.
4. **Severity.** BLOCKER = cannot execute safely (structure/scope/acceptance
   broken); MAJOR = should fix before execution; MINOR = cheap fix, note it.
   Assign by the effect on execution, not by annoyance.
5. **Verdict.** `PASS` iff zero BLOCKER findings (MAJOR/MINOR are listed and
   carried into the handoff as warnings). Otherwise `FAIL`.
6. Write `audit.json` (schema `planning/audit@2`, including the
   `grounding` block); gate with `plan-check.py validate`.

## Heuristics

- Quote, don't paraphrase: a finding without an artifact location is an
  opinion.
- Confirm, don't rubber-stamp: the deterministic layer is the floor, but an
  auditor who only forwards lint findings has not done the semantic pass —
  `checks_performed` must list the checks actually reasoned about.
- When in doubt between MAJOR and MINOR, ask "would the executor discover
  this mid-run, and at what cost?" — mid-run discovery is at least MAJOR.
- Independence > thoroughness: a fast isolated pass beats a thorough
  in-conversation one.

## Output

`<plan-dir>/audit.json` (schema `planning/audit@2`). Single writer.

## Failure & Escalation

- ≥ 1 BLOCKER → `verdict: FAIL` → orchestrator runs the targeted-revision loop
  (see `long-task-planning`); after 3 rounds, escalate to the user.
- Deterministic and semantic layers disagree (lint clean, semantic BLOCKER) →
  trust the semantic layer, record both in the finding.
- Auditor cannot verify a claim without the snapshot or a snapshot-listed
  file (e.g. a file outside `scan_boundary`) → note it as an assumption
  in `checks_performed`/notes, do not silently verify from memory, and do
  not walk the repo: the snapshot's `unknown_areas` is where such claims
  live, and a plan that depends on them has a grounding defect.

## Examples

**Good finding.**
`{id: F02, severity: BLOCKER, check: nondeterministic_acceptance, task_id: T03,
evidence: "tasks/T03.json acceptance_tests[1].description = 'responses should
feel complete and the endpoints work as expected', suggested_fix: 'replace with
observable cases — 202 body contains job_id; 404 body contains error.code
\"not_found\"; evidence pytest ...::test_submit_and_get'}`

**Anti-pattern.** Auditor runs in the same conversation that wrote the plan,
findings = "looks good overall, minor nits", verdict PASS, with
`planner_conversation_isolated: false` and no `checks_performed` — this is the
audit the whole skill set is built to prevent.
