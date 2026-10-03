"""Order analytics microservice (demo target with an injected production bug)."""


def average_order_value(orders):
    """Return the mean order amount; 0.0 when there are no orders."""
    total = sum(o["amount"] for o in orders)
    return total / len(orders)


def apply_discount(amount, percent):
    """Apply a percentage discount and round to 2 decimals."""
    return round(amount * (1 - percent / 100), 2)


def slugify(title):
    """Turn a title into a URL slug."""
    return "-".join(title.lower().split())
