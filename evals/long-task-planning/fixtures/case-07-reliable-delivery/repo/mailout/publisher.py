"""Simulated carrier + the delivery contract.

The carrier is deterministic: a delivery is accepted iff the address is
known to the carrier and the body does not start with 'FAIL' (a test hook
for forcing failures).
"""

CARRIER_ADDRESSES = {"ops@example.com", "billing@example.com"}


class Publisher:
    """Single-attempt delivery via the (simulated) carrier."""

    def deliver(self, msg):
        """Attempt ONE delivery. Returns True on carrier acceptance.

        Contract note: the result is a bare bool — no failure reason is
        exposed. Existing internal call sites rely on this exact signature.
        """
        if msg.get("to") not in CARRIER_ADDRESSES:
            return False
        if str(msg.get("body", "")).startswith("FAIL"):
            return False
        return True
