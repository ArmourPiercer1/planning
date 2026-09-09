"""Contact storage.

Contact shape: {"id": str, "name": str, "email": str,
                "tags": [str], "tagged_at": ISO str | None}
"""


class ContactStore:
    def __init__(self, contacts=None):
        self._contacts = {}
        for c in contacts or []:
            self.add(c)

    def add(self, contact):
        self._contacts[contact["id"]] = dict(contact)

    def get(self, contact_id):
        c = self._contacts.get(contact_id)
        return dict(c) if c else None

    def all(self):
        return [dict(c) for c in self._contacts.values()]
