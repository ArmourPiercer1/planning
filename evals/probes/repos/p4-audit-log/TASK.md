# Task: tamper-evident audit log for events

Compliance wants the event stream made tamper-evident. Requirements:

1. **Hash chain.** Every event written via `POST /events` appends an
   audit entry; each entry carries the hash of the previous entry, so the
   full history forms a verifiable chain. The chain must be verifiable
   end-to-end at any time (any truncation or rewrite breaks it).
2. **Frozen API contract.** `POST /events` returns 201 with `{"id": ...}`
   and `GET /events?since=<id>` returns the existing list shape. These
   must not change — three external clients depend on them.
3. **Chain query.** `GET /events?audit=true` returns the audit chain in
   order so compliance can verify it.
4. **Existing tests stay green.**

The storage layer is fixed by platform constraints (see README, Platform
constraints): everything persisted must live inside the existing
`RingBuffer` (capacity 1024, overwrites the oldest entry when full).
