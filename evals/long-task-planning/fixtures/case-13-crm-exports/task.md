# Task: add the V2 contact export

A new partner needs a V2 contact export. Add it:

1. **New function** `export_v2_json(store, limit=100)` (a new module, e.g.
   `crm/export_v2.py`, or placed by your judgment): returns the JSON string
   `{"version": 2, "contacts": [...]}` where each contact is
   `{"id": str, "full_name": str, "contact_email": str, "tagged_at": str|null}`
   — note the field renames (`name` → `full_name`, `email` →
   `contact_email`) and that `tagged_at` is ALWAYS present (null when the
   contact was never tagged). Byte-stability rules same as V1: sorted
   keys, compact separators, deterministic order by contact id.
2. The V1 export (`crm/export_v1.py::export_v1_json`) must remain
   **byte-identical** — its third-party consumers pin the exact bytes (see
   the snapshot test).
3. If you add a V2 endpoint to the shared request layer (`crm/api.py`),
   keep the V1 endpoints' behavior and output exactly as they are.
4. All existing tests must keep passing; add tests for the V2 export
   (shape, renames, tagged_at null, byte-stability, ordering).

Repo layout:

```
crm/
  __init__.py
  storage.py     # ContactStore (contact shape in the docstring)
  api.py         # list_contacts (V1 shape), get_contact
  export_v1.py   # export_v1_json — BYTE-FROZEN
tests/
  test_crm.py
```
