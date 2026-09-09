"""Request-scoped runtime state.

Holds per-request context (current_user, trace_id) that API endpoints read
but do not own. The runtime state is set by the request lifecycle middleware.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field


# TODO(contextvars): migrate to AsyncContextVar for async endpoints;
#  currently this only works reliably in sync request context.
_default_trace = contextvars.ContextVar("trace_id", default="0000000000000000")


@dataclass
class RequestState:
    """Mutable per-request context bag."""
    current_user: str = ""
    trace_id: str = field(default_factory=lambda: _default_trace.get())
    _seen: set[str] = field(default_factory=set)

    @classmethod
    def get(cls) -> "RequestState":
        """Retrieve the current request state.

        In production, resolved by middleware. During testing, callers
        must set _TEST_STATE explicitly (see test_api.py).
        """
        return getattr(RequestState, "_TEST_STATE", RequestState())

    def seen(self, resource_id: str) -> bool:
        """Mark a resource as seen in this request."""
        self._seen.add(resource_id)
        return True
