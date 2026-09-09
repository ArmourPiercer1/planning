# Case M — Meta-Planning Runaway Regression

A mature repo needs a significant feature added. The task is bounded but
complex: adding a notification pipeline with multiple delivery backends
(email, webhook, SMS) to an existing user service.

The repo has existing notification infrastructure that's tightly coupled to
user auth. The planner must decide whether to refactor the coupling or
build around it — an empirical question solvable by reading a few files.

**Expected behavior with v1.1:**
- At most ONE full audit before execution dispatch
- The seam-feasibility question is routed to a bounded SPIKE, not debated by reviewers
- Non-blocking findings are deferred as POST_STAGE
- Planning budget enforced (max_full_audits: 2)
- Time-to-first-evidence is sharp (first task is a spike or a concrete leaf)

**Trap:** The old behavior would spawn multiple reviewers to debate whether
the existing notification coupling is refactoring-worthy, each spawning
sub-reviewers, while never writing code.
