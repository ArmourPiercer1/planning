"""Device registry."""

_DEVICES = {
    "dev1": {"id": "dev1", "firmware": "2021", "name": "Rack A sensor"},
    "dev2": {"id": "dev2", "firmware": "2019", "name": "Legacy gate"},
}

LEGACY_FIRMWARE = "2019"


def get_device(device_id):
    """Return the device record, or None when unknown."""
    d = _DEVICES.get(device_id)
    return dict(d) if d else None


def is_legacy(device_id):
    """True for devices on the 2019 firmware (legacy wire format)."""
    d = _DEVICES.get(device_id)
    return bool(d and d.get("firmware") == LEGACY_FIRMWARE)
