"""Invoice creation and due-date computation."""

import datetime as _dt


def make_invoice(invoice_id, customer, amount, issued_date):
    """Create an invoice record in the shared store format.

    Fields: id, customer, amount, issued (ISO), due (ISO, +30 days),
    status ('open').
    """
    return {
        "id": invoice_id,
        "customer": customer,
        "amount": amount,
        "issued": issued_date,
        "due": (_dt.date.fromisoformat(issued_date) + _dt.timedelta(days=30)).isoformat(),
        "status": "open",
    }


def compute_due(invoice, today):
    """Compute the due state for an invoice as of today (ISO date).

    Returns {"status": "open"|"due"|"overdue", "days_overdue": int}.
    No late fee is computed yet.
    """
    due = _dt.date.fromisoformat(invoice["due"])
    t = _dt.date.fromisoformat(today)
    days = (t - due).days
    if days > 0:
        return {"status": "overdue", "days_overdue": days}
    if days == 0:
        return {"status": "due", "days_overdue": 0}
    return {"status": "open", "days_overdue": 0}
