"""Payslip text rendering."""

from payroll import employees
from payroll.calc import compute_pay


def render_payslip(employee_id):
    """Render a payslip as a list of text lines (no summary line yet)."""
    emp = employees.get_employee(employee_id)
    pay = compute_pay(emp)
    lines = [f"Payslip for {emp['name']} ({emp['id']})", ""]
    lines.append(f"Gross: {pay['gross']:.2f}")
    for name, amount in pay["deductions"]:
        lines.append(f"  - {name}: {amount:.2f}")
    lines.append(f"Net: {pay['net']:.2f}")
    return lines
