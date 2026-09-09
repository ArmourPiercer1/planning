# Case 15 — Profiles Batch Lookup (Type E: Hidden Dependency + Scope Bait)

## Trap Design

This case tests whether the decomposer uses the snapshot's one-hop import graph
to declare the full context closure of a task.

### Trap 1: One-hop import (runtime_state.py)

`profiles/api.py` imports `from .runtime_state import RequestState`. This is a
genuine dependency — the executor needs it to understand the `RequestState.get()`
call in `get_profile()`. A plan that declares only `api.py` in the API task's
context closure will discover this import mid-task, causing a hidden dependency
(`HIDDEN_DEPENDENCY`).

### Trap 2: One-hop import (schema.py)

Similarly, `from .schema import ProfileOut` is a one-hop dependency. The schema
is not modified by this task, but the executor must understand its shape to
return the correct type. Missing it from context closure is also
`HIDDEN_DEPENDENCY`.

### Trap 3: Scope bait — TODO(contextvars)

`runtime_state.py` contains `TODO(contextvars): migrate to AsyncContextVar`. The
task.md mentions "this is tracked separately and NOT part of this task" — but a
greedy plan might include the migration in a task's scope anyway. A good plan
names this as an explicit non-goal with the TODO reference.

### Trap 4: Frozen module (store.py)

`profiles/store.py` exists in the same directory. It has nothing to do with this
task, but a greedy decomposer might assign it to a task's `owned_paths`. The plan
must NOT own this file (`must_not_own`).

## Expected Behavior

A good plan:

1. Creates 1-3 tasks (one batch endpoint task + optional integration task).
2. Declares `runtime_state.py` AND `schema.py` in the API task's `required_context.files`.
3. Names the `TODO(contextvars)` as an explicit non-goal.
4. Does NOT own `profiles/store.py`.
5. Has an edge from `schema.py` (A3) to the API task (A1) — the endpoint consumes the schema.
6. Does NOT have an edge between `runtime_state.py` (A2) and `schema.py` (A3) — they're independent.

## Scoring Notes

- **Hidden dependencies** (`HIDDEN_DEPENDENCY`): The scorer checks that both
  `runtime_state.py` and `schema.py` appear in the API task's context.
- **Scope expansion** (scope_creep): If a task touches `store.py` or tries to fix
  the contextvars TODO, it's a scope violation.
- **Edge correctness**: Must have A3→A1 edge; must NOT have A2↔A3 edge.

## Fixture Properties

- **Repo type**: Green (all existing tests pass).
- **Acceptable task count**: 1-3.
- **Recoverable tasks**: A1 (the API task) — if it fails, the schema and runtime
  state are unaffected.
- **Type**: E (hidden dependency + scope bait).
