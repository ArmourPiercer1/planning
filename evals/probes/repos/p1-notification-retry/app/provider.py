"""Notification delivery provider client.

NOTE: 429 behavior is intentionally under-documented here. The provider
behind this client is a third-party gateway; the gateway's rate-limit
response shape is not in our docs. See tests for observed behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderResponse:
    status: int
    body: dict
    headers: dict = field(default_factory=dict)


class ProviderClient:
    """Client for the notification gateway.

    send(payload) -> ProviderResponse

    The gateway accepts a payload of the form:
        {"to": <user id>, "template": <template id>, "vars": {...}}
    and returns:
        202 {"accepted": true, "provider_ref": "..."}   on success
        4xx / 5xx {"error": "<message>"}                on failure

    Rate limiting: the gateway may return 429 under load. The exact
    semantics (Retry-After header? per-key or per-IP throttle? does a
    429 also reset our key's quota?) are not documented by the vendor.
    """

    def __init__(self, endpoint: str = "https://notify.example.invalid"):
        self.endpoint = endpoint
        self.calls: list[dict] = []

    def send(self, payload: dict) -> ProviderResponse:
        self.calls.append(payload)
        # Real implementation talks to the gateway over HTTP. The probe
        # fixture wires this to a fake in tests.
        raise NotImplementedError("wire to gateway in deployment")
