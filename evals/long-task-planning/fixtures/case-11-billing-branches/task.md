# Task: two independent billing features

Two features, delivered as **independent branches**: a failure or rework in
one must not force rework in the other.

**Branch 1 — late fees (billing/invoice.py)**
Invoices not paid by their due date incur a **5% late fee** on the amount.
Extend `compute_due` to return the fee and the adjusted total (e.g. keys
`late_fee`, `total_due`; `late_fee` is 0.0 when not overdue), and add
`late_fee: 0.0` to the record produced by `make_invoice` so stored records
carry the field.

**Branch 2 — refunded section (billing/reports.py)**
`daily_report` must gain a `"refunded"` section: a list of rows (same shape
as `rows`) for invoices **with status "refunded" that were issued on that
date**. The existing `rows`/`total` semantics are unchanged.

Both branches read/write the shared invoice record format in
`billing/store.py` — do not restructure it (additive optional fields are
fine). All existing tests must keep passing; add tests per branch.

Repo layout:

```
billing/
  __init__.py
  store.py       # InvoiceStore: add_invoice / invoices / find / update_status
  invoice.py     # make_invoice, compute_due
  reports.py     # daily_report(store, date_str)
tests/
  test_billing.py
```
