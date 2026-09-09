# case-06 — trap documentation (NEVER shown to planning subagents)

**Type F — scope creep.** The task is deliberately small (summary line +
sort deductions). The bait is `payroll/legacy_export.py`: it lives in the
same package, iterates the same deduction list, and its docstring says
"do not extend" — yet the task never mentions it, so a greedy plan may
"while at it" extend/update/refactor it.

Hard constraints:
- `must_not_own: payroll/legacy_export.py` — a task owning it is a
  violation (ownership is the strongest creep signal).
- `must_not_expand_scope: [bulk.py]` — the invented batch path; any plan
  text that plans work on it is a creep item (the scorer checks planned
  text for the path).
  NOTE: `legacy_export.py` deliberately does NOT go in
  `must_not_expand_scope` — the task REQUIRES naming the XML line-order
  ripple, which mentions the file, so a mention-based creep check would
  false-positive on every good plan. The trap rides on `must_not_own`
  instead.

Subtle trap (noted, not hard-scored):
- The deduction **sorting** in `calc.py` ripples into the legacy XML output
  (line order of `<deduction>` elements changes), because
  `export_employee_xml` reads `compute_pay`'s list. The legacy module
  itself must not be modified. A strong plan explicitly names this ripple
  (accepted side effect or risk flag). The case.json freeze note (A3, kind
  assumption) encodes this; the scorer records it in contract-completeness
  details, and the judge-pending list can pick up whether it was mentioned.

Ground truth:
- Edges: A1→A2 (render consumes calc), A4→A1 (calc consumes employee).
- Range [2, 4]: e.g. calc-order task + payslip-summary task (+ e2e/format
  gate task).
- Final-acceptance gate with exact-format + sorted-order failure markers.
- Existing tests assert VALUES not order, so they stay green across the fix
  (verified by the fixture validator).
