"""Carrier-facing SMS dispatch (simulated carrier, deterministic)."""

MAX_BODY_CHARS = 160


def send_sms(phone, body):
    """Send one SMS via the (simulated) carrier.

    Returns {"ok": bool, "carrier_response": str}.
    Carrier rules: empty phone rejected; bodies over 160 chars rejected.
    """
    if not phone or not str(phone).strip():
        return {"ok": False, "carrier_response": "REJECTED:bad-phone"}
    if len(body) > MAX_BODY_CHARS:
        return {"ok": False, "carrier_response": "REJECTED:body-too-long"}
    return {"ok": True, "carrier_response": "ACCEPTED"}
