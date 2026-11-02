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


def direct_mass_sum(model,q,pose):
    """Independent full-link FK formula; no compiled mass aggregation."""
    world=pose@np.linalg.inv(model.chains['base_link'].forward(q))
    moment=np.zeros(3);total=0.
    for link,(mass,point) in model.masses.items():
        moment+=mass*(world@model.chains[link].forward(q)@np.r_[point,1.])[:3]
        total+=mass
    return moment/total


def test_compiled_mass_matches_full_link_fk_over_named_joints_and_world_poses(nav_robot_model):
    rng=np.random.default_rng(1305)
    for _ in range(100):
        q={name:float(rng.uniform(bounds[0],bounds[1])) for name,bounds in nav_robot_model.limits.items()}
        axis=rng.normal(size=3);axis/=np.linalg.norm(axis);angle=rng.uniform(-np.pi,np.pi)
        x,y,z=axis;skew=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
        pose=np.eye(4);pose[:3,:3]+=np.sin(angle)*skew+(1-np.cos(angle))*(skew@skew)
        pose[:3,3]=rng.uniform(-2.,2.,size=3)
        assert np.allclose(com(nav_robot_model,q,pose),direct_mass_sum(nav_robot_model,q,pose),rtol=0.,atol=2e-12)


def test_compiled_mass_key_tracks_changed_model_inertial_data(nav_robot_model):
    q={name:0. for name in nav_robot_model.limits};pose=np.eye(4)
    first=com(nav_robot_model,q,pose)
    masses=dict(nav_robot_model.masses);mass,point=masses['base_link']
    masses['base_link']=(mass*2.,(.2,point[1],point[2]))
    changed=replace(nav_robot_model,masses=masses)
    assert np.allclose(com(changed,q,pose),direct_mass_sum(changed,q,pose),rtol=0.,atol=2e-12)
    assert np.linalg.norm(np.asarray(com(changed,q,pose))-first)>.001
    assert com(nav_robot_model,q,pose)==pytest.approx(first,abs=2e-12)


@pytest.mark.parametrize('mass,point',[(0.,(0.,0.,0.)),(-1.,(0.,0.,0.)),
    (float('nan'),(0.,0.,0.)),(1.,(0.,float('nan'),0.)),(1.,(0.,0.))])
def test_compiled_mass_rejects_invalid_static_input(nav_robot_model,mass,point):
    model=replace(nav_robot_model,masses={'base_link':(mass,point)})
    with pytest.raises(ValueError):com(model,{name:0. for name in model.limits},np.eye(4))
