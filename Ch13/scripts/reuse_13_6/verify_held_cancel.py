"""Actual canceled lift and retained physical grip; no full picking claim."""
import json
import sys
from verify_pick import verify

if __name__=='__main__':print(json.dumps([verify(p,held_cancel=True) for p in sys.argv[1:]],indent=2))
