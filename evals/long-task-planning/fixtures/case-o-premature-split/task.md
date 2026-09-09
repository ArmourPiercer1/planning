# Case O — Premature Stage Split

Two tasks: (1) Add a new index to an existing database table and update
queries, (2) Add a migration script for the same table. Both tasks share
the same database context, same table, same queries.

**Expected behavior with v1.1:**
- These are ONE leaf task (shared context, no intermediate evidence gain)
- No artificial stage boundary between them
- `stage_boundary` explains why a split is unnecessary
