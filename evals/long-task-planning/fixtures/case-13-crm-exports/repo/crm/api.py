"""CRM request layer (dict-based endpoints).

The list_contacts endpoint here serves the V1 wire shape — the same layer
will host new V2 endpoints. Changes to shared helpers must not alter V1
output bytes.
"""


def list_contacts(store, limit=100):
    """V1 endpoint shape: [{"id", "name", "email"}] ordered by id."""
    out = []
    for c in sorted(store.all(), key=lambda c: c["id"])[:limit]:
        out.append({"id": c["id"], "name": c["name"], "email": c["email"]})
    return out


def get_contact(store, contact_id):
    return store.get(contact_id)
