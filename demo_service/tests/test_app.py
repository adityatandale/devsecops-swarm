import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import apply_discount, average_order_value, slugify  # noqa: E402


def test_average_normal():
    assert average_order_value([{"amount": 10}, {"amount": 20}]) == 15


def test_average_empty_returns_zero():
    assert average_order_value([]) == 0.0


def test_discount():
    assert apply_discount(200, 10) == 180.0


def test_slugify():
    assert slugify("Hello Big World") == "hello-big-world"
