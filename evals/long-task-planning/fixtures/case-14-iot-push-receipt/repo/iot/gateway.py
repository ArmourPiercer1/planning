"""Push gateway (fire-and-forget in V1)."""

from iot import devices

# V1 fire-and-forget log (module level; to be superseded by the event log).
EVENTS = []


class Gateway:
    """Pushes payloads to devices.

    V1 contract: push(payload) -> None. Existing internal call sites invoke
    push() and ignore the return value.
    """

    def push(self, payload):
        """Push a payload to a device (payload: {"device_id", "data"}).

        V1 behavior: unknown devices and invalid payloads are silently
        ignored; nothing is returned. This is the observability gap.
        """
        dev = devices.get_device(payload.get("device_id"))
        if dev is None:
            EVENTS.append({"device_id": payload.get("device_id"), "accepted": False})
            return None
        EVENTS.append({"device_id": dev["id"], "accepted": True})
        return None
