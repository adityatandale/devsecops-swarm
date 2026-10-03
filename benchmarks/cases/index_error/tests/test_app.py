import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import first_item, last_item

def test_last(): assert last_item([1, 2, 3]) == 3
def test_last_empty(): assert last_item([]) is None
def test_first(): assert first_item([4, 5]) == 4
