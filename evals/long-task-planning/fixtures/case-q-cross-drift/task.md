# Case Q — Cross-Stage Drift

Stage 1 plan was to add a reporting subsystem. Stage 2 checkpoint tries to
also introduce an admin dashboard — a non-goal in the original project contract.

**Expected behavior with v1.1:**
- Drift check detects `scope_added` contains admin dashboard work
- `requirements_removed` or `acceptance_changed` flagged if original
  acceptance criteria were silently dropped
- Stage completion marked as having drift requiring replan
