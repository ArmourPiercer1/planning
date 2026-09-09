"""Pay calculation for a single employee."""


def compute_pay(employee):
    """Compute gross, deductions, net for an employee record.

    employee: {"id", "name", "hourly", "hours"}
    Returns {"gross": float, "deductions": [(name, amount), ...], "net": float}.

    NOTE: deduction order is currently insertion order (tax, then
    insurance). Finance requires a stable, deterministic order for
    statements and the upcoming summary line.
    """
    gross = round(employee["hourly"] * employee["hours"], 2)
    tax = round(gross * 0.20, 2)
    insurance = round(gross * 0.05, 2)
    deductions = [("tax", tax), ("insurance", insurance)]
    net = round(gross - sum(a for _, a in deductions), 2)
    return {"gross": gross, "deductions": deductions, "net": net}
