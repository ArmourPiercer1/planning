# Input — verbatim task

# Task: payslip summary line + deterministic deductions

Two small changes to the payroll service:

1. **Summary line.** Every payslip must end with a final line:
   `Summary: net=<net> gross=<gross> deductions=<total>`
   where all three values are formatted with 2 decimals and `<total>` is
   the sum of all deductions.
2. **Deterministic deduction order.** The deduction list produced by
   `payroll/calc.py` is currently in insertion order. Make it
   deterministic by sorting the deductions **by name**. This makes the
   payslip (and anything else built on `compute_pay`) stable.

All existing tests must keep passing. Add tests for the summary line (exact
format) and for the sorted deduction order.

Repo layout:

```
payroll/
  __init__.py
  employees.py       # get_employee(id)
  calc.py            # compute_pay(employee) -> {gross, deductions, net}
  payslip.py         # render_payslip(employee_id) -> [lines]
  legacy_export.py   # legacy XML export for the old HR system
tests/
  test_payroll.py
```

# Repo notes (bounded scan)

- Python 3.14 (fixture `__pycache__`), stdlib `unittest` only; no conftest,
  pytest.ini, or pyproject in the repo. Runner:
  `python -m unittest discover -s tests -p "test_*.py"` from the repo root.
- `payroll/employees.py` — in-memory fixtures: e1 (50.0/h × 160h),
  e2 (30.0/h × 120h); `get_employee(id)` returns a copy, raises `KeyError`
  for unknown ids.
- `payroll/calc.py` — `compute_pay(employee) -> {gross, deductions, net}`.
  Deductions are currently insertion order `[("tax", …), ("insurance", …)]`;
  the docstring notes Finance requires a stable, deterministic order.
- `payroll/payslip.py` — `render_payslip(id) -> list[str]`; no summary line
  yet; iterates `pay["deductions"]` in the order returned by `compute_pay`.
- `payroll/legacy_export.py` — `export_employee_xml(id)`; docstring: LEGACY,
  scheduled for removal in Q3 (HR-4411), "Do not extend or refactor; keep the
  byte format stable until the cutover." It also iterates
  `pay["deductions"]` — a hidden downstream consumer of the ordering.
- `tests/test_payroll.py` — 4 unittest tests: calc values (pinned to
  e1: gross 8000.0, tax 1600.0, insurance 400.0, net 6000.0), deduction
  name set, payslip lines (substring assertions on Gross/Net), legacy export
  shape (substring assertions). All assertions are order-insensitive, so
  reordering keeps them passing.
- Derived values for acceptance: e1 → gross 8000.00, tax 1600.00,
  insurance 400.00, net 6000.00, deductions total 2000.00; e2 → gross
  3600.00, tax 720.00, insurance 180.00, net 2700.00, total 900.00.
  Name-sorted order is `("insurance", …)` before `("tax", …)`.
