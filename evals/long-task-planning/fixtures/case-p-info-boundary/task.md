# Case P — Information-Gain Boundary

A short spike determines which of two architectural routes to take for a
feature. The spike probes whether an existing library supports the needed
integration pattern.

**Expected behavior with v1.1:**
- Stage ends AFTER the spike completes
- `next_planning_trigger` is emitted (normal: stage_acceptance_reached)
- Detailed plan for the feature only covers the spike; the post-spike
  implementation is in `horizons.forecast`
- Two forecast stages defined: Route A (library works) and Route B (needs
  custom integration)
