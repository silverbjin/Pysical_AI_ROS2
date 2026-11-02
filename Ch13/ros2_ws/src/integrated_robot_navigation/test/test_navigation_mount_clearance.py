"""Break caught: navigation hip spacing ignored or legacy geometry changed."""
from pathlib import Path
import xacro
import pytest

from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.leg_kinematics import fk_leg


def test_opt_in_mount_clearance_preserves_original_default():
    path = Path(__file__).resolve().parents[2] / 'integrated_robot_description/urdf/robot_system.urdf.xacro'
    original = compile_model(xacro.process_file(str(path)).toxml())
    navigation = compile_model(xacro.process_file(str(path), mappings={'hip_mount_y': '0.13'}).toxml())
    assert fk_leg(original, 'fr_foot', (0., -.5, 1.))[1] == pytest.approx(-.15)
    assert fk_leg(navigation, 'fr_foot', (0., -.5, 1.))[1] == pytest.approx(-.18)
