"""Field validators (raise ValueError on invalid input)."""


def validate_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    if len(name) > 120:
        raise ValueError("name too long (max 120)")


def validate_email(email):
    if not isinstance(email, str) or "@" not in email or email.startswith("@"):
        raise ValueError("email must contain @ not at position 0")
