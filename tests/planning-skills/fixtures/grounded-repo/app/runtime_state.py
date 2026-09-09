"""Per-request state carried through the profile pipeline."""


class RequestState:
    """Mutable per-request state.

    TODO: migrate RequestState to contextvars (non-blocking; a later Stage).
    """

    def __init__(self) -> None:
        self.values: dict = {}
