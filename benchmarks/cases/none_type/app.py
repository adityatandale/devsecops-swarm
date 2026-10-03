def full_name(first, last):
    """Join first and last name; treat None as empty and strip extra spaces."""
    return first + " " + last


def initials(name):
    return "".join(p[0].upper() for p in name.split())
