"""Statement rendering (reporting views over the ledger)."""


def render_statement(txns):
    """Render a list of transactions to statement text lines.

    One line per txn: 'YYYY-MM-DD  kind     +amount' or '-amount' for debits.
    """
    lines = []
    for t in txns:
        sign = "-" if t["kind"] == "debit" else "+"
        lines.append(f'{t["date"]}  {t["kind"]:8s} {sign}{abs(t["amount"])}')
    return lines


# NOTE: the reporting team's draft assumed the ledger API returns
# {"results": [...], "cursor": ...}. This helper is UNVERIFIED against the
# real API — check bank/api.py before using it.
def _iter_api_page(page):
    """Yield transactions from one API page (draft: unverified shape)."""
    for t in page.get("results", []):
        yield t
