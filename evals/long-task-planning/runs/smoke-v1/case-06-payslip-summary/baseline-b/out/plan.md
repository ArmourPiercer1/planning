# Plan — Payslip Summary Line (case-06-payslip-summary)

Conventional engineering plan. Planning only — nothing in this document is to
be implemented until the plan is approved.

## Task understanding

The repo is a small in-memory payroll service:

- `payroll/employees.py` — two fixture employees (`e1` Ada L.: 50.0 × 160.0;
  `e2` Bo M.: 30.0 × 120.0); `get_employee()` returns a copy.
- `payroll/calc.py` — `compute_pay(employee)` returns
  `{"gross", "deductions": [(name, amount), ...], "net"}`. Its docstring notes
  that "Finance requires a stable, deterministic order for statements and the
  upcoming summary line" — i.e., a **summary line is expected but not yet
  implemented**.
- `payroll/payslip.py` — `render_payslip(employee_id)` returns text lines:
  header, gross, one line per deduction, net. Docstring: "no summary line yet".
- `payroll/legacy_export.py` — legacy XML export, marked **LEGACY, HR-4411:
  scheduled for removal in Q3; do not extend or refactor; keep the byte format
  stable until the cutover.**
- `tests/test_payroll.py` — unittest suite; "all must keep passing".

**Interpreted goal** (from the case name and the code hints): add a
per-payslip **summary line** to the payslip output — a total-deductions line,
e.g. `Total deductions: 2000.00`, placed between the itemized deduction lines
and the `Net:` line — while (a) keeping every existing test green, (b) keeping
the deduction order deterministic (tax, then insurance), and (c) leaving the
legacy XML byte-identical.

Assumption (flagged): the summary is per-employee inside the payslip, not a
payroll-wide aggregate report. If the requester means an all-employees
aggregate, see Out of scope and revisit phase 2 before implementation.

## Phases

### Phase 1 — Baseline and contract freeze
Rationale: capture the exact current behavior before any change so that
post-change diffs are attributable, and freeze the output contracts (summary
line format, position, legacy XML bytes) that the change must respect.

Todos:
- [ ] Run `python -m unittest discover -s tests -v` and record a green baseline.
- [ ] Snapshot the exact current output of `render_payslip("e1")` (list of lines) in a scratch note outside the repo.
- [ ] Snapshot the exact current output of `export_employee_xml("e1")` (string) in the same scratch note.
- [ ] Freeze the contract: summary line format `Total deductions: <N.NN>` (2 decimals, half-even rounding of the sum of the already-rounded deduction amounts), inserted immediately before the `Net:` line; deduction order stays (tax, insurance); legacy XML bytes unchanged.

### Phase 2 — Implement the summary line in the payslip renderer
Rationale: the smallest change surface is `payroll/payslip.py` — the module that owns text rendering. `calc.py` keeps producing what it produces (read-only consumer), which keeps the deterministic-order note satisfied without touching calculation code.

Todos:
- [ ] In `payroll/payslip.py`, compute `total_deductions = round(sum(a for _, a in pay["deductions"]), 2)`.
- [ ] Insert `lines.append(f"Total deductions: {total_deductions:.2f}")` after the deduction loop and before the `Net:` line.
- [ ] Update the stale docstring ("no summary line yet") to describe the new line.

### Phase 3 — Tests for the new behavior
Rationale: lock in the new line's format and exact position, and add an
independent regression guard for the frozen legacy format, so future changes
cannot silently move or reword the summary line or disturb the XML.

Todos:
- [ ] Add a test asserting `render_payslip("e1")` contains `Total deductions: 2000.00` (1600.00 tax + 400.00 insurance).
- [ ] Add a test asserting position: the line immediately before `Net: 6000.00` in the returned list is the summary line (index-based check, not just `assertIn`).
- [ ] Add a test for the second employee: `render_payslip("e2")` contains `Total deductions: 900.00` (720.00 tax + 180.00 insurance) and `Net: 2700.00`.
- [ ] Add a byte-level regression test: `export_employee_xml("e1")` equals the exact Phase 1 snapshot string.

### Phase 4 — Verification and handoff
Rationale: prove no regressions with both the suite and explicit diffs
against the Phase 1 baselines, then commit a single clean change.

Todos:
- [ ] Run the full suite: `python -m unittest discover -s tests -v` — all tests pass (old + new).
- [ ] Cross-check arithmetic: for e1 the summary (2000.00) equals the sum of the itemized deduction lines shown on the slip; net = gross − summary.
- [ ] Diff the new `render_payslip("e1")` output against the Phase 1 snapshot: the only difference is the added summary line; header, gross, deduction order, and net lines are untouched.
- [ ] Diff the legacy XML output against the Phase 1 snapshot: byte-identical.
- [ ] Commit with a message such as "Add total-deductions summary line to payslip".

## Implementation checklist (explicit step order)

1. Run the existing suite; record the green baseline.
2. Snapshot current `render_payslip("e1")` lines and `export_employee_xml("e1")` string.
3. Edit `payroll/payslip.py`: add the summary line between the deduction lines and the `Net:` line; fix the stale docstring.
4. Edit `tests/test_payroll.py`: add the new tests (format for e1, position, e2 values, legacy XML byte snapshot).
5. Run the full suite.
6. Diff the new payslip output against the step 2 snapshot; confirm only the summary line was added.
7. Diff the legacy XML output against the step 2 snapshot; confirm byte-identical.
8. Commit.

Dependencies (prose):
- Step 3 happens after step 1 because the baseline must be green before any
  change; otherwise a failure after the change could be pre-existing and we
  could not attribute it to the change.
- Step 3 happens after step 2 because the snapshot is the diff target for
  steps 6 and 7 and freezes the exact current format the summary line must
  not disturb (including the trailing `Net:` line).
- Step 4 happens after step 3 because the tests assert against the concrete
  line that step 3 produces (format string and position); writing them first
  would also be a valid TDD order, but this plan verifies the produced output
  empirically against the frozen contract from Phase 1.
- Step 5 happens after steps 3 and 4 because the suite must exercise the
  changed renderer and the new tests together.
- Steps 6 and 7 happen after step 5 because a green suite plus an explicit
  byte-for-byte diff against the baseline is the strongest evidence that the
  legacy contract (HR-4411) and the payslip layout are intact; running the
  diffs before the suite could waste effort on a build that does not even
  compile or import.
- Step 8 happens last because committing before steps 5–7 would record an
  unverified state in history.

## Testing & verification

- Full suite: `python -m unittest discover -s tests -v` — every test must
  pass, including all pre-existing assertions in `TestCalc`, `TestPayslip`,
  and `TestLegacyExport` (unchanged).
- New-behavior tests (Phase 3):
  - `render_payslip("e1")` contains `Total deductions: 2000.00`.
  - The line immediately before `Net: 6000.00` is the summary line.
  - `render_payslip("e2")` contains `Total deductions: 900.00` and `Net: 2700.00`.
  - `export_employee_xml("e1")` is byte-equal to the Phase 1 snapshot.
- Regression checks:
  - `TestLegacyExport.test_export_shape` passes unmodified.
  - Gross/net values for both employees are unchanged (8000.00 / 6000.00 for
    e1; 3600.00 / 2700.00 for e2).
  - Deduction order on the rendered slip remains tax, then insurance
    (deterministic, per the Finance note in `calc.py`).
- Manual sanity: print the rendered e1 slip; visually confirm the layout:
  header, blank line, gross, two deduction lines, summary line, net.

## Out of scope

- Any change to `payroll/legacy_export.py` — byte format is frozen until the
  Q3 cutover (HR-4411); do not extend or refactor, and do not add a summary
  element to the XML.
- Changes to `payroll/calc.py` values or deduction order — computation and
  the (tax, insurance) order stay exactly as they are; the summary only
  consumes `compute_pay` output read-only.
- A payroll-wide / all-employees aggregate report — this case is the
  per-payslip summary line only.
- New employees, tax/insurance rate changes, or new deduction types.
- Refactoring `payroll/employees.py` or replacing the in-memory fixtures.
- Modifying any existing test assertion — the test file gets additions only.
- CI configuration, packaging, or dependency changes.
