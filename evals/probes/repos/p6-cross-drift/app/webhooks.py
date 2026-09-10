"""Webhook dispatch infra (existing; fire-and-forget)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WebhookLog:
    sent: list[dict] = field(default_factory=list)


class WebhookDispatcher:
    """Sends a payload to a URL. Fixture: records the send, returns 200.

    Real deployment talks HTTP; failures are logged and swallowed by
    design (notifications must never break the main transaction).
    """

    def __init__(self, log: WebhookLog | None = None):
        self.log = log or WebhookLog()

    def send(self, url: str, payload: dict) -> int:
        self.log.sent.append({"url": url, "payload": payload})
        return 200
