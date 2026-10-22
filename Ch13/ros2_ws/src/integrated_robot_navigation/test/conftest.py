"""Source tests deliberately depend only on chapter 13 packages."""
from pathlib import Path
import sys
import pytest
import xacro

SRC = Path(__file__).resolve().parents[2]
for package in ('integrated_robot_navigation', 'integrated_robot_vision'):
    sys.path.insert(0, str(SRC / package))


@pytest.fixture
def robot_model():
    from integrated_robot_navigation.model import compile_model
    path = SRC / 'integrated_robot_description/urdf/robot_system.urdf.xacro'
    return compile_model(xacro.process_file(str(path)).toxml())
