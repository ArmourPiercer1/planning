"""Tax computation.

NOTE: this is one of the 'other callers' of commerce.rules.round_money
that the rounding audit EXPLICITLY excludes — its rounding behavior must
not change.
"""

from commerce.rules import round_money

TAX_RATE = 0.10


def tax_amount(subtotal):
    """Tax for a subtotal, rounded with the shared default mode."""
    return round_money(subtotal * TAX_RATE)
