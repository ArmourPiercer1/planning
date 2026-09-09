# Planning Run — Baseline A (Free-form Agent Planning)

You are given a software task and a repository. Plan how you would implement
the task the way you normally would: explore the repo as needed, then write
your plan as a single markdown document at `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\baseline-a\out/plan.md`.

Use your own judgment about structure, ordering, and level of detail. No
special planning skills, schemas, or required output format are provided, and
you must not invent a structured artifact set (no JSON plan files, no DAG
tooling).

You are NOT allowed to implement anything — planning only. Do not modify any
file in the repo.

## Telemetry (mandatory)

Every time you read a file, append one JSON line to `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\baseline-a\telemetry.jsonl`:
`{"ts":"<iso>","op":"read","path":"<path>"}`.

## Hard rules

- Work only inside `D:\AI_Coworking\skill-build\planning\evals\long-task-planning\runs\smoke-v1\case-10-timeout-seam\baseline-a\work\repo`.
- Never read evaluation files (case definitions, expected constraints, trap
  documentation). If you encounter a directory named `fixtures`, `expected`,
  or `reports`, do not open it.

## Finish

Write `DONE` plus a 2-line summary of your plan as your final message.
