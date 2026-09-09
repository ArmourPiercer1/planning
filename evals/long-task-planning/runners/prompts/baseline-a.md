# Planning Run — Baseline A (Free-form Agent Planning)

You are given a software task and a repository. Plan how you would implement
the task the way you normally would: explore the repo as needed, then write
your plan as a single markdown document at `{plan_out}/plan.md`.

Use your own judgment about structure, ordering, and level of detail. No
special planning skills, schemas, or required output format are provided, and
you must not invent a structured artifact set (no JSON plan files, no DAG
tooling).

You are NOT allowed to implement anything — planning only. Do not modify any
file in the repo.

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
