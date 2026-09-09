# Plan — Payslip Summary Line + Deterministic Deduction Order

Repo: `work/repo` (single commit `88dffe5 "fixture baseline"`, clean tree, Python 3.14 per `__pycache__`, unittest-based tests, no external deps, no package manifest).

## 1. Task (from `task.md`)

1. Every payslip must end with a final line
   `Summary: net=<net> gross=<gross> deductions=<total>` — all three values with 2 decimals, `<total>` = sum of all deductions.
2. `payroll/calc.py` currently returns deductions in insertion order; make it deterministic by sorting the deductions **by name**.
3. All existing tests must keep passing; add tests for the summary line (exact format) and the sorted deduction order.

## 2. What I found in the repo (every file read)

| File | Role | Notes |
|---|---|---|
| `payroll/__init__.py` | package marker, docstring only | no changes needed |
| `payroll/employees.py` | in-memory fixture: `e1` (50.0/h × 160 h), `e2` (30.0/h × 120 h) | no changes needed |
| `payroll/calc.py` | `compute_pay(employee) -> {"gross", "deductions": [(name, amount)...], "net"}`. Builds `[("tax", 20%), ("insurance", 5%)]` in insertion order; docstring NOTE explicitly says order is insertion order and Finance requires a stable order | **primary change** |
| `payroll/payslip.py` | `render_payslip(employee_id) -> [lines]`: header, blank, `Gross:`, one line per deduction, `Net:`. Docstring: "(no summary line yet)" | **primary change** |
| `payroll/legacy_export.py` | `export_employee_xml(employee_id)`: legacy XML, iterates `pay["deductions"]` in whatever order `compute_pay` returns. Module docstring: *"LEGACY … Do not extend or refactor; keep the byte format stable until the cutover"* (HR-4411) | **trap — see D2** |
| `tests/test_payroll.py` | 4 tests, all order-agnostic (dict lookups, sets, `assertIn`) | extends with new tests |
| `tests/__init__.py` | empty | no changes |

`compute_pay` has exactly two consumers in the repo: `payslip.py` and `legacy_export.py`. There are no other callers, no CLI, no other packages.

Expected values (hand-computed, used by the new tests):

- **e1:** gross `8000.00`, tax `1600.00`, insurance `400.00`, net `6000.00`, deductions total `2000.00`
- **e2:** gross `3600.00`, tax `720.00`, insurance `180.00`, net `2700.00`, deductions total `900.00`

## 3. Design decisions

### D1 — Sort inside `compute_pay` (`calc.py`)

The task explicitly requires the deduction list **produced by `payroll/calc.py`** to be sorted by name, so the sort belongs in `compute_pay`, not at the call sites.

- After building the list: `deductions = sorted(deductions, key=lambda d: d[0])` (lexicographic by name → `insurance` before `tax`).
- `net` is computed from the list, so it is unaffected by order (sum is order-independent).
- Update the docstring: remove/replace the NOTE about insertion order, document "deductions returned sorted by name (deterministic)".

### D2 — The legacy-export trap: pin the legacy render order (the key risk of this task)

Sorting in `compute_pay` propagates to **both** consumers. For `payslip.py` that is exactly what the task wants. For `legacy_export.py` it is a conflict: the module's own header says *"Do not extend or refactor; keep the byte format stable until the cutover."* Today its `<deduction>` elements come out as `tax` then `insurance` (insertion order); after D1 the same loop would emit `insurance` then `tax` — a byte-level change to a format that must stay stable.

Crucially, the existing suite would **not** catch this: `test_export_shape` only uses `assertIn` on substrings, so it passes with either order. The regression is silent.

Decision (recommended): make a minimal, targeted edit in `legacy_export.py` to pin the historical order, so its output stays **byte-identical** to today's:

```python
# historical render order of the old HR system — do not reorder (HR-4411)
_LEGACY_DEDUCTION_ORDER = ("tax", "insurance")
```

and iterate:

```python
order = {n: i for i, n in enumerate(_LEGACY_DEDUCTION_ORDER)}
for name, amount in sorted(pay["deductions"],
                           key=lambda d: order.get(d[0], len(order))):
```

- Known names render in the exact legacy order (`tax`, then `insurance`) regardless of `compute_pay`'s order.
- Unknown future names fall through deterministically (after known names, in sorted order), so the export stays deterministic even if a new deduction type appears before cutover.
- This is a preservation change (keeps documented behavior), not a refactor of the legacy format: same tags, same attribute layout, same byte sequence for all current employees.

Alternatives considered and rejected:

- **(a) Leave `legacy_export.py` untouched** — simplest, all tests pass, but the XML byte format changes (element order swaps), directly violating the module's stated constraint. Not acceptable when the constraint is written into the file.
- **(b) Sort only in `payslip.py` / at call sites** — would leave the legacy output stable, but the task explicitly requires the list *produced by `calc.py`* to be sorted, so other consumers of `compute_pay` would still see insertion order. Doesn't satisfy the stated requirement.

### D3 — Summary line in `render_payslip` (`payslip.py`)

- The payslip is defined by `render_payslip`; the summary is appended as the **last element** of the returned list.
- Format exactly: `Summary: net={pay['net']:.2f} gross={pay['gross']:.2f} deductions={total:.2f}`.
- `total = round(sum(a for _, a in pay["deductions"]), 2)` — sum the already-rounded per-deduction amounts (the same amounts Finance reports per line) and round once for display safety. Using the sum of the deduction list (rather than `gross - net`) matches the spec: "`<total>` is the sum of all deductions".
- `net`/`gross` come from `compute_pay` — no recomputation, single source of truth.
- No summary line goes into the legacy XML: the spec says *payslips* end with the summary, and the legacy module is frozen.
- Update the module/function docstring (drop "no summary line yet").

## 4. Implementation steps (in order)

1. **Baseline snapshot (verification artifact, outside the repo).** From the repo root run:
   `python -c "from payroll.legacy_export import export_employee_xml; print(export_employee_xml('e1'), export_employee_xml('e2'), sep='\n---\n')"`
   and save the output to a scratch file under `baseline-a/out/` (e.g. `legacy_baseline.txt`). This is the reference for the byte-stability check in step 6. (The repo itself is not modified; the working tree is clean at `88dffe5`, so a `git stash`-style diff against HEAD would be an equivalent fallback.)
2. **`payroll/calc.py`** — sort deductions by name in `compute_pay`; update the docstring NOTE (D1).
3. **`payroll/legacy_export.py`** — add `_LEGACY_DEDUCTION_ORDER` and the order-pinning iteration (D2). Nothing else in this file changes.
4. **`payroll/payslip.py`** — append the summary line as the final line of `render_payslip`; update docstring (D3).
5. **`tests/test_payroll.py`** — add the new tests (section 5), keeping the existing 4 tests untouched.
6. **Verify** (section 6): full test suite green + legacy XML byte-identical to the step-1 snapshot + visual check of a rendered payslip.

Files changed: `payroll/calc.py`, `payroll/legacy_export.py`, `payroll/payslip.py`, `tests/test_payroll.py`. No other file is touched.

## 5. Test plan

### Existing tests (must stay green — they are all order-agnostic, which is why D2 needs its own guard)

- `TestCalc.test_compute_pay_values` — dict lookup by name: unaffected by order.
- `TestCalc.test_deductions_covers_all_names` — set comparison: unaffected.
- `TestPayslip.test_render_payslip_lines` — `lines[0]` header + `assertIn` for Gross/Net: appending a final line doesn't disturb them.
- `TestLegacyExport.test_export_shape` — `assertIn` only: passes either way; **does not pin order** (hence the new test below).

### New tests (added to `tests/test_payroll.py`)

1. **`TestCalc.test_deductions_sorted_by_name`**
   - e1 exact: `pay["deductions"] == [("insurance", 400.0), ("tax", 1600.0)]`.
   - Generic guard: `[n for n, _ in compute_pay(get_employee("e2"))["deductions"]] == sorted(names)`.
2. **`TestPayslip.test_summary_line_exact_format`**
   - e1: `lines[-1] == "Summary: net=6000.00 gross=8000.00 deductions=2000.00"`.
   - e2: `lines[-1] == "Summary: net=2700.00 gross=3600.00 deductions=900.00"`.
   - Exact-string assert (per the task's "exact format" requirement) and the `lines[-1]` index asserts it is the final line.
3. **`TestLegacyExport.test_export_keeps_legacy_deduction_order`**
   - `xml = export_employee_xml("e1")`; assert `xml.index('name="tax"') < xml.index('name="insurance"')`.
   - Pins the legacy byte order that the pre-existing suite can't catch; fails if step 3 is ever dropped.

## 6. Verification

1. From the repo root: `python -m unittest discover -s tests -v` → all 7 tests (4 existing + 3 new) pass.
2. **Byte-stability check:** re-run the step-1 export command and diff against `out/legacy_baseline.txt` → must be identical for both employees.
3. Spot-check: print `render_payslip("e1")` and eyeball the full slip — header, gross, `insurance`/`tax` lines in sorted order, net, and the `Summary:` line last.
4. `git status` / `git diff` — confirm only the four intended files changed.

## 7. Non-goals / out of scope

- No new deduction types, tax rates, or changes to `employees.py` data.
- No structural changes to the legacy XML (no new elements, no attribute changes); no summary line in the XML.
- No CLI, no new dependencies, no packaging changes; `payroll/__init__.py` and `tests/__init__.py` untouched.
- No refactoring of the legacy module beyond the single order-pinning change required by its own frozen-format constraint.

## 8. Risks / notes

- **Silent legacy-order regression is the main trap of this task** — the existing suite's `assertIn` checks pass even if the XML order swaps. Mitigated by the explicit order-pinning edit (D2), the new order test, and the pre/post byte snapshot comparison.
- Floating point: amounts are already `round(…, 2)` in `compute_pay`; the summary sums the rounded amounts and uses `:.2f`, so there is no display drift for the current (and any future two-decimal) data.
- If a new deduction name is introduced before the legacy cutover, the legacy export stays deterministic (unknown names sort after known ones); the payslip and summary pick it up automatically in sorted order.
