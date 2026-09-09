"""Discount rule definitions and the default registry."""


class Rule:
    """A multiplicative percentage rule.

    name: stable identifier.
    factor: multiplier applied when the rule matches (0.95 == 5% off).
    predicate: callable(customer_ctx) -> bool.
    """

    def __init__(self, name, factor, predicate):
        self.name = name
        self.factor = factor
        self.predicate = predicate

    def __repr__(self):
        return f"Rule({self.name}, factor={self.factor})"


def default_registry():
    """Rules applied by default, in order.

    Order is irrelevant for the result: factors multiply (commutative).
    """
    return [
        Rule("new_customer", 0.95, lambda ctx: bool(ctx.get("new_customer"))),
    ]
