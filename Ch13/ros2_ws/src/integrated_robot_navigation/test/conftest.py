"""Source tests deliberately depend only on chapter 13 packages."""
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[2]
for package in ('integrated_robot_navigation', 'integrated_robot_vision'):
    sys.path.insert(0, str(SRC / package))
