"""Only this chapter's source packages are available to pure Python tests."""
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / 'ros2_ws' / 'src'
for name in ('integrated_robot_vision', 'integrated_robot_runtime'):
    sys.path.insert(0, str(SRC / name))
