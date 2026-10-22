"""Break caught: atan2 principal branch discarding a valid bounded thigh pose."""
import pytest

from integrated_robot_navigation.leg_kinematics import fk_leg, ik_leg


def test_inverse_retains_valid_thigh_above_pi(robot_model):
    q = (0., 3.8, .4)
    target = fk_leg(robot_model, 'fr_foot', q)
    assert ik_leg(robot_model, 'fr_foot', target, previous=q) == pytest.approx(q, abs=1e-7)
