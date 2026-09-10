"""Observed provider behavior (gateway capture, unannotated by vendor)."""
from __future__ import annotations

import unittest

from app.provider import ProviderClient, ProviderResponse


class FakeGatewayClient(ProviderClient):
    """Mimics the gateway as observed in staging captures.

    The 429 branch below was copied from a staging trace: the gateway
    returned 429 with the body shown, and NO Retry-After header. Whether
    that was quota, burst, or a per-key throttle was never confirmed.
    """

    def __init__(self):
        super().__init__()
        self._rate_limited_once = False

    def send(self, payload: dict) -> ProviderResponse:
        self.calls.append(payload)
        if not self._rate_limited_once:
            self._rate_limited_once = True
            # Observed in staging: 429, error body, no Retry-After header.
            return ProviderResponse(
                status=429,
                body={"error": "rate limited"},
                headers={"x-gateway": "edge-3"},
            )
        return ProviderResponse(
            status=202,
            body={"accepted": True, "provider_ref": f"ref-{len(self.calls)}"},
        )


class TestObservedGateway(unittest.TestCase):
    def test_second_call_after_429_succeeds(self):
        client = FakeGatewayClient()
        first = client.send({"to": "u1", "template": "t", "vars": {}})
        self.assertEqual(first.status, 429)
        self.assertNotIn("Retry-After", first.headers)
        second = client.send({"to": "u1", "template": "t", "vars": {}})
        self.assertEqual(second.status, 202)


if __name__ == "__main__":
    unittest.main()
