# Case O — Premature Stage Split

## What this tests

A regression fixture for the failure mode where the planner splits work into
separate stages or tasks without intermediate evidence gain. When two pieces
of work share the same context (same database, same table, same queries),
splitting them creates coordination overhead without gaining information.

## The trap

The planner sees "add index" and "add migration" as two separate concerns and
creates two tasks, possibly even two stages. But they require loading the same
database schema, the same migration framework, and the same query files. An
agent doing one already has all the context for the other.

## What v1.1 fixes

- **Context closure** recognizes that both tasks load the same files and concepts
- **No split without evidence gain** — a split is only justified when the first
  part produces information the second part needs
- **Stage boundary rationale** explains why merging is better

## Scoring

| Criterion | Weight | Description |
|-----------|--------|-------------|
| no_unnecessary_split | 3 | shared-context tasks kept as one leaf |
| merge_rationale_present | 2 | split_rationale explains shared context |
