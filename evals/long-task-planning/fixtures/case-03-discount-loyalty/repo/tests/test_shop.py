"""Tests for the shop pricing service (all must keep passing)."""

import unittest

from shop import loyalty
from shop.discounts import Rule
from shop.pricing import PricingEngine


class TestPricing(unittest.TestCase):
    def test_no_matching_rules(self):
        engine = PricingEngine()
        item = {"base_price": 100.0, "qty": 1, "customer": {}}
        self.assertEqual(engine.compute(item), 100.0)

    def test_new_customer_rule(self):
        engine = PricingEngine()
        item = {"base_price": 100.0, "qty": 1, "customer": {"new_customer": True}}
        self.assertEqual(engine.compute(item), 95.0)

    def test_rounds_once_at_end(self):
        engine = PricingEngine(rules=[Rule("a", 0.99, lambda ctx: True),
                                     Rule("b", 0.99, lambda ctx: True)])
        self.assertEqual(engine.compute({"base_price": 100.0, "qty": 1, "customer": {}}), 98.01)

    def test_custom_engine_rules(self):
        engine = PricingEngine(rules=[])
        self.assertEqual(engine.compute({"base_price": 33.333, "qty": 1, "customer": {}}), 33.33)


class TestLoyalty(unittest.TestCase):
    def test_known_and_unknown_customers(self):
        self.assertEqual(loyalty.get_tier("c1"), "gold")
        self.assertEqual(loyalty.get_tier("nobody"), "bronze")

    def test_set_tier_rejects_unknown(self):
        with self.assertRaises(ValueError):
            loyalty.set_tier("c1", "platinum")


if __name__ == "__main__":
    unittest.main()
