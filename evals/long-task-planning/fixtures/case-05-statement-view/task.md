# Task: wire the statement view to the ledger API

`bank/views.py` can render a transaction list, but there is no function that
pulls a user's history out of the ledger. Implement it:

1. Add `statement_for(ledger, user)` to `bank/views.py`. It must:
   - fetch the user's **full** transaction history from
     `Ledger.list_transactions`, **following pagination cursors** until the
     listing is exhausted;
   - return `render_statement(all_txns)` (the list of text lines, oldest
     first).
2. `bank/api.py` (the `Ledger` API) must NOT be changed — it is the
   canonical source of the wire shape.
3. All existing tests must keep passing. Add tests for `statement_for`,
   including one where the history spans **more than one page** (use a small
   `limit`, e.g. 2 or 3 transactions per page).

Repo layout:

```
bank/
  __init__.py
  models.py      # TXN_FIELDS, make_txn(...)
  api.py         # Ledger: add / list_transactions(user, cursor, limit)
  views.py       # render_statement(txns), _iter_api_page(page) [draft]
tests/
  test_bank.py
```
