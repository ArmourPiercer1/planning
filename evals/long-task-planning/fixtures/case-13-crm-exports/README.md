# case-13 — trap documentation (NEVER shown to planning subagents)

**Hybrid C+E — shared layer collision + frozen-byte seam.**

C-side (fake parallelism on the shared layer):
- The new V2 endpoint lands in `crm/api.py`; the V1-protection work
  (guards, snapshot regression) also wants api.py. Two parallel tasks both
  owning api.py = collision.
- `forbidden_parallel_pairs: [A1, A3]` on `crm/api.py` fires only when
  both tasks OWN api.py and are unordered (scorer rule).
- `parallelizable_groups: [A1, A3]` says the opposite is legal: parallel
  V2 work + V1 protection **iff** api.py has a single owner.

E-side (hidden seam with pinned bytes):
- `export_v1_json` output is byte-pinned by
  `TestExportV1.test_v1_byte_snapshot` (sorted keys, compact separators).
- The lazy plan "unifies" both exports through a shared serializer in
  api.py — V1 bytes at risk. The gate markers (byte/identical/regression/
  snapshot/diff) require the plan to NAME the V1 regression check.
- V2 contract details: `tagged_at` always present (null, not omitted —
  the inverse of case-08's omission rule; the contract_consistency gate
  markers full_name/contact_email/tagged_at catch sloppy shape work).

Ground truth:
- Edges A2→A1, A2→A3 (data from the store).
- Range [3, 6], cap 2: V2 export task + V1-protection/guard task + e2e
  gate task(s), with api.py owned by exactly one task.
- A1 recoverable (checkpoint handoff on the shared-layer task).
- Scope bait: emails/dashboard/imports.
