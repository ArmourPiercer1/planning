# Task: rounding audit fix

A finance audit found that two domains round inconsistently. Fix:

1. **Sales**: `commerce/sales.py` `order_total` must round with **HALF_UP**
   to cents. (Its current test pins the old default-mode value; update that
   test to the finance-required value — the test file says so in its
   docstring.)
2. **Inventory**: `commerce/inventory.py` `apply_cost_adjustment` must round
   with **HALF_EVEN**, pinned **explicitly** (pass the mode in the call) so
   a future default-mode change cannot drift this domain. The numeric
   result for current inputs does not change.
3. **Other callers must not change.** `commerce/tax.py` (and any other
   caller of `commerce.rules.round_money`) must keep exactly its current
   rounding behavior. `tests/test_commerce.py::TestTax` must pass
   **unchanged**.

You may add modes/helpers to `commerce/rules.py` if you think they help,
but nothing requires changing it. All other existing tests must keep
passing.

Repo layout:

```
commerce/
  __init__.py
  rules.py       # round_money(x, mode=None), DEFAULT_MODE, _MODES
  sales.py       # order_total(items)
  inventory.py   # apply_cost_adjustment(cost, delta)
  tax.py         # tax_amount(subtotal) — audit-EXCLUDED caller
tests/
  test_commerce.py
```
