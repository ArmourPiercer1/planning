"""Tests for the commerce rounding behavior.

NOTE: TestSales pins the CURRENT (pre-audit) sales rounding. The rounding
fix task explicitly allows updating that test to the finance-required
value. TestTax must pass UNCHANGED.
"""

import unittest

from commerce import inventory, sales, tax
from commerce.rules import round_money


class TestRules(unittest.TestCase):
    def test_default_half_even(self):
        self.assertEqual(round_money(2.665), 2.66)

    def test_half_up_mode(self):
        self.assertEqual(round_money(2.665, "HALF_UP"), 2.67)

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            round_money(1.0, "NOPE")


class TestSales(unittest.TestCase):
    def test_order_total_current_rounding(self):
        # pins current default-mode behavior (HALF_EVEN): to be updated by
        # the rounding fix task to the finance-required HALF_UP value
        self.assertEqual(sales.order_total([{"price": 1.005, "qty": 1}]), 1.00)

    def test_order_total_plain(self):
        self.assertEqual(sales.order_total([{"price": 0.1, "qty": 3}]), 0.30)


class TestInventory(unittest.TestCase):
    def test_cost_adjustment_current(self):
        # 10.005 rounds to 10.00 under HALF_EVEN (unchanged by the fix)
        self.assertEqual(inventory.apply_cost_adjustment(10.0, 0.005), 10.0)


class TestTax(unittest.TestCase):
    def test_tax_behavior_unchanged(self):
        # 26.65 * 0.10 = 2.665 -> HALF_EVEN -> 2.66 (would be 2.67 under
        # HALF_UP: this test is the regression guard for 'other callers')
        self.assertEqual(tax.tax_amount(100.0), 10.0)
        self.assertEqual(tax.tax_amount(26.65), 2.66)


if __name__ == "__main__":
    unittest.main()
