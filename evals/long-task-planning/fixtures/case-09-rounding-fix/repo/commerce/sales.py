"""Order totals (sales domain)."""

from commerce.rules import round_money


def order_total(items):
    """items: [{'price': float, 'qty': int}, ...] -> total rounded to cents.

    Current: uses round_money's default mode. Finance requires HALF_UP for
    order totals (see task).
    """
    total = sum(i["price"] * i["qty"] for i in items)
    return round_money(total)
