# Case N — Too-Far Planning

Design a migration from a monolithic service to a microservice architecture
in phases. The first phase splits off the reporting subsystem; the second
phase splits the user subsystem; the third phase introduces an event bus.

**Expected behavior with v1.1:**
- Current detailed plan covers ONLY the reporting subsystem split (Phase 1)
- Future phases remain as forecast-stage entries with objective + depends_on_evidence
- Phase 2 and 3 do NOT get detailed DAGs or Task Packages
- `stage_boundary.stop_after` ends at the point where Phase 1 evidence is gained
- `horizons.forecast` lists Phase 2 and 3 with their dependency on Phase 1 evidence
