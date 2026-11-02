"""One bounded arithmetic call, identical current measured-q mass model.

No simulator, ROS lifecycle or reference permission is provided by this core.
"""
from dataclasses import replace
import importlib
import math

import numpy as np
import pytest
from test_center_of_mass import direct_mass_sum
from test_mass_frame_budget import CountedPositions


def evaluator(model):
    name='integrated_robot_navigation.native_mass'
    assert importlib.util.find_spec(name), 'bounded native mass arithmetic missing'
    return importlib.import_module(name).NativeMassEvaluator(model)


def test_native_mass_matches_independent_full_link_fk_at_current_named_q(nav_robot_model):
    core=evaluator(nav_robot_model)
    rng=np.random.default_rng(130528)
    for _ in range(100):
        q={name:float(rng.uniform(bounds[0],bounds[1])) for name,bounds in nav_robot_model.limits.items()}
        axis=rng.normal(size=3);axis/=np.linalg.norm(axis);angle=rng.uniform(-math.pi,math.pi)
        x,y,z=axis;skew=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
        pose=np.eye(4);pose[:3,:3]+=math.sin(angle)*skew+(1-math.cos(angle))*(skew@skew)
        pose[:3,3]=rng.uniform(-10.,10.,size=3)
        assert np.allclose(core(nav_robot_model,q,pose),direct_mass_sum(nav_robot_model,q,pose),rtol=0.,atol=2e-12)
    assert core.provenance['scope']=='pure_current_q_mass_arithmetic_no_state_or_command'
    assert len(core.provenance['library_sha256'])==64
    core.close()
    with pytest.raises(RuntimeError,match='closed'):core(nav_robot_model,q,pose)


def test_native_mass_does_not_cache_measured_poses_and_reads_each_joint_once(nav_robot_model):
    with evaluator(nav_robot_model) as core:
        q=CountedPositions({name:0. for name in nav_robot_model.limits})
        first=core(nav_robot_model,q,np.eye(4))
        assert set(q.reads)==set(nav_robot_model.limits) and max(q.reads.values())==1
        q['arm_joint_2']=.5
        assert np.linalg.norm(np.asarray(core(nav_robot_model,q,np.eye(4)))-first)>.001
        q['arm_joint_2']=0.
        assert core(nav_robot_model,q,np.eye(4))==pytest.approx(first,abs=2e-12)


def test_native_mass_binds_exact_model_and_inertial_data(nav_robot_model):
    q={name:0. for name in nav_robot_model.limits};pose=np.eye(4)
    masses=dict(nav_robot_model.masses);mass,point=masses['base_link'];masses['base_link']=(mass*2.,(.2,*point[1:]))
    changed=replace(nav_robot_model,masses=masses)
    with evaluator(changed) as core:
        assert core(changed,q,pose)==pytest.approx(direct_mass_sum(changed,q,pose),abs=2e-12)
        with pytest.raises(ValueError,match='model'):core(nav_robot_model,q,pose)


@pytest.mark.parametrize('pose',[np.diag([2.,1.,1.,1.]),np.diag([-1.,1.,1.,1.]),
    np.full((4,4),float('nan')),np.eye(3)])
def test_native_mass_rejects_non_rigid_input(nav_robot_model,pose):
    with evaluator(nav_robot_model) as core:
        with pytest.raises(ValueError):core(nav_robot_model,{name:0. for name in nav_robot_model.limits},pose)


@pytest.mark.parametrize('kind',['missing','nan','limit'])
def test_native_mass_rejects_invalid_current_joints(nav_robot_model,kind):
    q={name:0. for name in nav_robot_model.limits}
    if kind=='missing':del q['fr_thigh_joint']
    elif kind=='nan':q['fr_thigh_joint']=float('nan')
    else:q['fr_thigh_joint']=nav_robot_model.limits['fr_thigh_joint'][1]+1.
    with evaluator(nav_robot_model) as core:
        with pytest.raises(ValueError):core(nav_robot_model,q,np.eye(4))
