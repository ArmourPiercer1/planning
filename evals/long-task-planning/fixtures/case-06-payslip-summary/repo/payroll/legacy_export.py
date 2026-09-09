"""Legacy XML export for the old HR system.

LEGACY: scheduled for removal in Q3 (see HR-4411). Do not extend or
refactor; keep the byte format stable until the cutover.
"""

from payroll import employees
from payroll.calc import compute_pay


def export_employee_xml(employee_id):
    emp = employees.get_employee(employee_id)
    pay = compute_pay(emp)
    parts = ["<payroll>", f"  <employee>{emp['id']}</employee>"]
    parts.append(f"  <gross>{pay['gross']:.2f}</gross>")
    for name, amount in pay["deductions"]:
        parts.append(f'  <deduction name="{name}">{amount:.2f}</deduction>')
    parts.append(f"  <net>{pay['net']:.2f}</net>")
    parts.append("</payroll>")
    return "\n".join(parts)
