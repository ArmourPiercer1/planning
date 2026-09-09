"""Invoice record storage.

The record format here is the SHARED contract between the billing features
and the reporting features: both read and write these dicts.
"""


class InvoiceStore:
    def __init__(self):
        self._invoices = []

    def add_invoice(self, record):
        self._invoices.append(dict(record))
        return record

    def invoices(self):
        return [dict(r) for r in self._invoices]

    def find(self, invoice_id):
        for r in self._invoices:
            if r["id"] == invoice_id:
                return dict(r)
        return None

    def update_status(self, invoice_id, status):
        for r in self._invoices:
            if r["id"] == invoice_id:
                r["status"] = status
        return self.find(invoice_id)
