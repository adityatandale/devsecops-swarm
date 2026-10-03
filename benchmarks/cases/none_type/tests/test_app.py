import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import full_name, initials

def test_full(): assert full_name("Ada", "Lovelace") == "Ada Lovelace"
def test_none_first(): assert full_name(None, "Lovelace") == "Lovelace"
def test_none_last(): assert full_name("Ada", None) == "Ada"
def test_initials(): assert initials("ada lovelace") == "AL"
