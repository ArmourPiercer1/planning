"""Employee records (in-memory fixture data)."""

_EMPLOYEES = {
    "e1": {"id": "e1", "name": "Ada L.", "hourly": 50.0, "hours": 160.0},
    "e2": {"id": "e2", "name": "Bo M.", "hourly": 30.0, "hours": 120.0},
}


def get_employee(employee_id):
    """Return a copy of the employee record."""
    return dict(_EMPLOYEES[employee_id])
