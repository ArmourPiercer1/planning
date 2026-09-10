# eventstore (probe fixture)

A small event service. Clients POST events; clients GET them back.
Storage is a fixed-size ring buffer — a platform constraint, not a
design choice we can revisit (see Platform constraints below).

## Layout

- `app/events.py` — `EventAPI`: `post_event()`, `list_events()`.
- `app/storage.py` — `RingBuffer`: the storage layer.
- `tests/test_events.py` — the suite that must stay green.

## Platform constraints (fixed)

- The service runs on an embedded platform with a strict memory cap.
  The storage layer (`RingBuffer`, capacity 1024) **cannot be replaced,
  extended, or run alongside a second store**: the platform allocator is
  sized for exactly one store instance, and the platform team has
  confirmed no change is possible this release cycle. Any new persisted
  data structure must live inside the existing `RingBuffer`.
