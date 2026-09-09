"""Legacy wire formatter for the 2019 firmware.

LEGACY: the 2019 firmware speaks this exact string format. Do not modify,
do not deprecate, without a firmware cutover (see F-201).
"""


def format_legacy(payload):
    """Format a payload for the 2019 firmware: 'v1|<device_id>|<len(data)>'."""
    data = str(payload.get("data", ""))
    return f"v1|{payload.get('device_id', '?')}|{len(data)}"
