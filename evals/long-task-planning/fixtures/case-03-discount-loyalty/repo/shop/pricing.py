"""Pricing engine: applies percentage rules multiplicatively, rounds once."""

from shop.discounts import default_registry


class PricingEngine:
    """Applies the registered rules to an item.

    A rule matches when its predicate accepts the customer context; matching
    rules are applied multiplicatively. Rounding to cents happens exactly
    once, at the end of compute().
    """

    def __init__(self, rules=None):
        self.rules = list(rules) if rules is not None else default_registry()

    def compute(self, item):
        """Price an item: {'base_price': float, 'qty': int, 'customer': dict}.

        Returns the final price rounded to cents.
        """
        price = float(item["base_price"])
        ctx = item.get("customer", {})
        for rule in self.rules:
            if rule.predicate(ctx):
                price *= rule.factor
        return round(price, 2)
