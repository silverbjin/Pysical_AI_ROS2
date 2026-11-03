import sys
from pathlib import Path
packages=Path(__file__).resolve().parents[2]
for name in ('ch13_navigation_reuse','ch13_manipulation_reuse'):
    sys.path.insert(0,str(packages/name))
