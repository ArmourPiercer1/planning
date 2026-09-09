# Planning Run — Baseline B (Conventional Checklist Planning)

Plan the task using a conventional engineering plan format. The plan document
at `{plan_out}/plan.md` must contain:

- **Phases** — ordered, with a short rationale each;
- a **Todo list** per phase;
- an **implementation checklist** with explicit step order; dependencies
  between steps described in prose ("step 4 happens after step 2 because …");
- a **Testing & verification** section;
- an **Out of scope** section.

No special planning skills, schemas, or DAG tooling are provided; do not use
any. You are NOT allowed to implement anything — planning only. Do not modify
any file in the repo.

## Telemetry (mandatory)

Every time you read a file, append one JSON line to `{telemetry_file}`:
`{"ts":"<iso>","op":"read","path":"<path>"}`.

## Hard rules

- Work only inside `{work_dir}`.
- Never read evaluation files (case definitions, expected constraints, trap
  documentation). If you encounter a directory named `fixtures`, `expected`,
  or `reports`, do not open it.

## Finish

Write `DONE` plus a 2-line summary of your plan as your final message.
