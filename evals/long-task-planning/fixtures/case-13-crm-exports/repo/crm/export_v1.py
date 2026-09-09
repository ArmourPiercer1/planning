"""V1 JSON export for existing third-party consumers.

BYTE-FROZEN: downstream consumers pin the exact bytes (sorted keys,
compact separators, deterministic order by contact id). Do not change the
output of this function.
"""

import json

from crm.api import list_contacts


def export_v1_json(store, limit=100):
    payload = {"version": 1, "contacts": list_contacts(store, limit)}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
