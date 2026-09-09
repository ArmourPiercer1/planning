# Task: bulk discount + loyalty discount

Two pricing features, both stacking on top of the existing rules:

1. **BULK**: orders with `qty >= 10` get an additional 5% off (factor 0.95).
2. **LOYALTY**: gold-tier customers (see `shop/loyalty.py`, `get_tier`)
   get an additional 10% off (factor 0.90).

Composition rules (already true for the existing rules, and must remain
true):

- all applicable percentage rules are multiplicative;
- the final price is rounded to cents exactly once, at the end;
- existing rule behavior (e.g. `new_customer`) must not change.

Do not change the public behavior of `PricingEngine.compute` for items that
match no new rule. All existing tests must keep passing; add tests proving
the new rules compose — including an item that matches bulk + loyalty +
new_customer together, and a gold customer ordering 10 units.

The repo layout:

```
shop/
  __init__.py
  pricing.py     # PricingEngine.compute(item) — applies registry rules
  discounts.py   # Rule(name, factor, predicate), default_registry()
  loyalty.py     # TIERS, get_tier(customer_id), set_tier(...)
tests/
  test_shop.py
```
