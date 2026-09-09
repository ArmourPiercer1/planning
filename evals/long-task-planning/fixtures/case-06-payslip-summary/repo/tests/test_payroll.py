"""Tests for the payroll service (all must keep passing)."""

import unittest

from payroll import employees
from payroll.calc import compute_pay
from payroll.legacy_export import export_employee_xml
from payroll.payslip import render_payslip


class TestCalc(unittest.TestCase):
    def test_compute_pay_values(self):
        pay = compute_pay(employees.get_employee("e1"))
        self.assertEqual(pay["gross"], 8000.0)
        self.assertEqual(dict(pay["deductions"])["tax"], 1600.0)
        self.assertEqual(dict(pay["deductions"])["insurance"], 400.0)
        self.assertEqual(pay["net"], 6000.0)

    def test_deductions_covers_all_names(self):
        pay = compute_pay(employees.get_employee("e2"))
        self.assertEqual({n for n, _ in pay["deductions"]}, {"tax", "insurance"})


class TestPayslip(unittest.TestCase):
    def test_render_payslip_lines(self):
        lines = render_payslip("e1")
        self.assertIn("Payslip for Ada L. (e1)", lines[0])
        self.assertIn("Gross: 8000.00", lines)
        self.assertIn("Net: 6000.00", lines)


class TestLegacyExport(unittest.TestCase):
    def test_export_shape(self):
        xml = export_employee_xml("e1")
        self.assertIn("<gross>8000.00</gross>", xml)
        self.assertIn("<net>6000.00</net>", xml)
        self.assertIn('<deduction name="tax">', xml)
        self.assertIn("</payroll>", xml)


if __name__ == "__main__":
    unittest.main()
