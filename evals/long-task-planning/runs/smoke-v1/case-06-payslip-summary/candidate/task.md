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
