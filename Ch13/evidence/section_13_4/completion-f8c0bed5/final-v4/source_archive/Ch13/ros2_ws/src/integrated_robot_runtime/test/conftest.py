from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[2]
for name in ('integrated_robot_runtime', 'integrated_robot_vision'):
    sys.path.insert(0, str(SRC / name))
