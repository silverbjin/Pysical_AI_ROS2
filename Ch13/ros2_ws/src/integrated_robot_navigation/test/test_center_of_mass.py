"""Breaks caught: unweighted averaging, wrong world frame, invalid poses."""
from dataclasses import replace
import importlib

import numpy as np
import pytest


def com(model, joints, pose):
    assert importlib.util.find_spec('integrated_robot_navigation.support'), 'CoM core missing'
    return importlib.import_module('integrated_robot_navigation.support').center_of_mass(
        model, joints, pose)


def test_mass_weighting_and_world_pose(robot_model):
    # Hand fixture: base mass1 at x0; hip mass3 at base x.4/y0.
    model = replace(robot_model, masses={'base_link': (1., (0., 0., 0.)),
                                         'fr_hip_link': (3., (.15, .1, 0.))})
    q = {j: 0. for j in robot_model.limits}
    assert com(model, q, np.eye(4)) == pytest.approx((.3, 0., 0.))
    pose = np.array([[0., -1., 0., 1.], [1., 0., 0., 2.],
                     [0., 0., 1., 3.], [0., 0., 0., 1.]])
    assert com(model, q, pose) == pytest.approx((1., 2.3, 3.))


def test_com_uses_actual_joint_position(robot_model):
    model = replace(robot_model, masses={'fr_thigh_link': (1., (0., 0., -.125))})
    q = {j: 0. for j in robot_model.limits}
    q['fr_thigh_joint'] = np.pi / 2
    assert com(model, q, np.eye(4)) == pytest.approx((.125, -.15, 0.), abs=1e-10)


def test_com_rejects_non_rigid_body_pose(robot_model):
    with pytest.raises(ValueError):
        com(robot_model, {j: 0. for j in robot_model.limits}, np.diag([2., 1., 1., 1.]))
