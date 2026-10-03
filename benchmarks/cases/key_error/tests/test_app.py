import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import get_email, normalize

U = {"1": {"email": "a@x.com"}, "3": {}}

def test_known(): assert get_email(U, "1") == "a@x.com"
def test_unknown_user(): assert get_email(U, "2") is None
def test_no_email(): assert get_email(U, "3") is None
def test_normalize(): assert normalize("  AbC ") == "abc"
