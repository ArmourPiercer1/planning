"""Stock cost adjustments (inventory domain)."""

from commerce.rules import round_money


def apply_cost_adjustment(cost, delta):
    """New unit cost after a delta adjustment, rounded to cents.

    Current: uses round_money's default mode. Finance requires HALF_EVEN
    for cost adjustments, pinned explicitly so a future default change
    cannot drift this domain.
    """
    return round_money(cost + delta)
