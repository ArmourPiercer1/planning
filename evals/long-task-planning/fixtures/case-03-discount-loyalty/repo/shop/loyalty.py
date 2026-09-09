"""Loyalty tiers (membership data)."""

TIERS = ("bronze", "silver", "gold")

_CUSTOMERS = {
    "c1": "gold",
    "c2": "silver",
    "c3": "bronze",
}


def get_tier(customer_id):
    """Return the tier for a customer; unknown customers are bronze."""
    return _CUSTOMERS.get(customer_id, "bronze")


def set_tier(customer_id, tier):
    """Override a customer's tier (used by tests and the admin path)."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier: {tier}")
    _CUSTOMERS[customer_id] = tier
