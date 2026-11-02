"""Breaks caught: undersized body footprint, sampling-only rotation bounds."""
import importlib
import math

import pytest


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.carry_profile'), 'footprint missing'
    return importlib.import_module('integrated_robot_navigation.carry_profile')


def test_body_and_attitude_swept_volume_have_real_margin(nav_robot_model):
    robot_model = nav_robot_model
    module = api()
    p = module.prepare_profile(robot_model, (0., 1.2, -2., 0., .8, 0.))
    footprint = module.swept_footprint(robot_model, p, module.default_limits())
    xs, ys = [v[0] for v in footprint], [v[1] for v in footprint]
    assert max(xs) >= .35 and min(xs) <= -.35
    assert max(ys) >= .20 and min(ys) <= -.20
    assert len(footprint) == 4
    assert p.inflation_radius >= max(math.hypot(x, y) for x, y, _ in footprint) + .05


def test_interval_rotation_contains_interior_extremum():
    module = api()
    lo, hi = module.trig_bounds('sin', 0., math.pi)
    assert lo <= 0. and hi >= 1.  # endpoints alone both equal zero
    lo, hi = module.trig_bounds('cos', -math.pi/2, math.pi/2)
    assert lo <= 0. and hi >= 1.


def test_carry_config_mismatch_cannot_reuse_small_footprint(nav_robot_model):
    robot_model = nav_robot_model
    module = api()
    p = module.prepare_profile(robot_model, (0., 1.2, -2., 0., .8, 0.))
    limits = module.default_limits()
    limits['max_roll_pitch'] = .16
    with pytest.raises(ValueError, match='config'):
        module.swept_footprint(robot_model, p, limits)


def test_interval_dependency_refinement_keeps_front_approach_usable(nav_robot_model):
    module = api()
    p = module.prepare_profile(nav_robot_model, (0., 1.2, -2., 0., .8, 0.))
    # Largest standoff .65m must leave .05m for the stationary fixture face.
    # This bounds overestimation; it is not permission to truncate geometry.
    assert max(v[0] for v in p.footprint) <= .60


def test_footprint_contains_independent_native_geometry_with_margin(nav_robot_model):
    import mujoco
    import numpy as np
    from integrated_robot_navigation.geometry import navigation_mjcf
    module = api()
    p = module.prepare_profile(nav_robot_model, (0., 1.2, -2., 0., .8, 0.))
    model = mujoco.MjModel.from_xml_string(navigation_mjcf(nav_robot_model))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    rng = np.random.default_rng(13503)
    footprint = np.array(p.footprint)
    for _ in range(24):
        for name in nav_robot_model.joint_names:
            lo, hi = p.limits['gait_joint_bounds'][name.split('_')[1]]
            data.qpos[model.joint(name).qposadr[0]] = rng.uniform(lo, hi)
        for i, q in enumerate(p.arm_q, 1):
            data.qpos[model.joint('arm_joint_'+str(i)).qposadr[0]] = q + rng.uniform(-.03, .03)
        mujoco.mj_forward(model, data)
        roll, pitch = rng.uniform(-.15, .15, 2)
        rx = np.array([[1., 0., 0.], [0., np.cos(roll), -np.sin(roll)],
                       [0., np.sin(roll), np.cos(roll)]])
        ry = np.array([[np.cos(pitch), 0., np.sin(pitch)], [0., 1., 0.],
                       [-np.sin(pitch), 0., np.cos(pitch)]])
        attitude = ry @ rx
        # Offline coordinate projection only; no root pose writes or physics steps.
        for g in range(model.ngeom):
            kind, size = model.geom_type[g], model.geom_size[g]
            if kind == mujoco.mjtGeom.mjGEOM_PLANE:
                continue
            center = attitude @ (data.geom_xpos[g] - data.body('base_link').xpos)
            rotation = attitude @ data.geom_xmat[g].reshape(3, 3)
            if kind == mujoco.mjtGeom.mjGEOM_BOX:
                extent = np.abs(rotation) @ size
            elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
                extent = np.full(3, size[0])
            elif kind == mujoco.mjtGeom.mjGEOM_CAPSULE:
                extent = size[0] + np.abs(rotation[:, 2]) * size[1]
            else:
                extent = (size[0] * np.sqrt(rotation[:, 0]**2 + rotation[:, 1]**2)
                          + size[1] * np.abs(rotation[:, 2]))
            assert np.all(center[:2] + extent[:2] + .05 <= footprint[:, :2].max(axis=0) + 1e-9)
            assert np.all(center[:2] - extent[:2] - .05 >= footprint[:, :2].min(axis=0) - 1e-9)
