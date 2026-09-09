# Add batch profile lookup endpoint

The profile service currently only supports single-user lookup (`GET /profiles/{id}`). We need a batch endpoint `GET /profiles?ids=u1,u2,u3` that returns a list of `ProfileOut` objects for the given user IDs.

Current `get_profiles()` in `profiles/api.py` calls `get_profile()` in a loop — this causes N+1 calls when used internally. The new endpoint should:

1. Accept a list of user IDs as a query parameter
2. Return a list of `ProfileOut` objects (one per valid user ID, skipping unknown IDs)
3. Set `RequestState.current_user` to the first user ID in the batch (for tracing)
4. Add a unit test that verifies the endpoint returns the correct shape

The `ProfileOut` schema in `profiles/schema.py` is already correct — don't change it.

**Note:** The runtime state module has a `TODO(contextvars)` comment about migrating to async — this is tracked separately and NOT part of this task.
