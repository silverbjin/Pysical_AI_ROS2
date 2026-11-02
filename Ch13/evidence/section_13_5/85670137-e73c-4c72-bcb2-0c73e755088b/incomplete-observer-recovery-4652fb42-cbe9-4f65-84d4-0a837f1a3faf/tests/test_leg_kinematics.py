"""Breaks caught: axis/sign, wrong branch, clipping unreachable feet."""
import importlib
from pathlib import Path

import numpy as np
import pytest


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.leg_kinematics'), 'leg IK missing'
    return importlib.import_module('integrated_robot_navigation.leg_kinematics')


def test_literal_standing_foot_positions(robot_model):
    k = api()
    assert k.fk_leg(robot_model, 'fr_foot', (0., -.5, 1.)) == pytest.approx(
        (.25, -.15, -.438791280945), abs=1e-10)
    assert k.fk_leg(robot_model, 'fl_foot', (0., -.5, 1.)) == pytest.approx(
        (.25, .15, -.438791280945), abs=1e-10)


@pytest.mark.parametrize('q', [(.2, -.7, 1.2), (-.1, .6, -1.2)])
def test_ik_preserves_nearest_valid_knee_branch(robot_model, q):
    k = api()
    for foot in robot_model.feet:
        p = k.fk_leg(robot_model, foot, q)
        actual = k.ik_leg(robot_model, foot, p, previous=q)
        assert actual == pytest.approx(q, abs=1e-7)


@pytest.mark.parametrize('p', [(.25, -.15, -2.), (float('nan'), 0., 0.),
                              (.25, -.1, 0.)])
def test_unreachable_or_nonfinite_is_not_clipped(robot_model, p):
    with pytest.raises(ValueError):
        api().ik_leg(robot_model, 'fr_foot', p, previous=(0., -.5, 1.))


def test_urdf_fk_matches_independent_native_model(robot_model):
    import mujoco
    k = api()
    path = Path(__file__).resolve().parents[2] / 'integrated_robot_description/mujoco/robot_system.xml'
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    rng = np.random.default_rng(135)
    # Offline FK inputs only: no physics step, root pose write, ROS or viewer.
    for _ in range(8):
        for foot in robot_model.feet:
            q = tuple(rng.uniform([-.2, -.7, .6], [.2, -.3, 1.4]))
            for part, value in zip(('hip', 'thigh', 'calf'), q):
                joint = model.joint(foot[:2] + '_' + part + '_joint')
                data.qpos[joint.qposadr[0]] = value
            mujoco.mj_forward(model, data)
            base = data.body('base_link')
            native = base.xmat.reshape(3, 3).T @ (data.body(foot).xpos - base.xpos)
            assert k.fk_leg(robot_model, foot, q) == pytest.approx(native, abs=1e-5)
