"""Daily reports over the invoice store."""


def daily_report(store, date_str):
    """One row per invoice issued on date_str, plus totals.

    Returns {"rows": [{"id","customer","amount","status"}], "total": float}.
    """
    rows = []
    total = 0.0
    for inv in store.invoices():
        if inv["issued"] == date_str:
            rows.append({"id": inv["id"], "customer": inv["customer"],
                         "amount": inv["amount"], "status": inv["status"]})
            total += inv["amount"]
    return {"rows": rows, "total": total}
