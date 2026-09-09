"""Shared rounding rules.

Multiple domains round through round_money; the default mode is HALF_EVEN
(banker's rounding). Domains that need a different mode must pass it
explicitly.
"""

from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

_MODES = {"HALF_UP": ROUND_HALF_UP, "HALF_EVEN": ROUND_HALF_EVEN}
DEFAULT_MODE = "HALF_EVEN"


def round_money(x, mode=None):
    """Round to cents using the given mode (default: HALF_EVEN)."""
    key = mode or DEFAULT_MODE
    if key not in _MODES:
        raise ValueError(f"unknown rounding mode: {key}")
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=_MODES[key]))
