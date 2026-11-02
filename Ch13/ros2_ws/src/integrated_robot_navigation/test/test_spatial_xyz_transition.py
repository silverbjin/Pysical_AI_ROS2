"""Bounded stance XYZ is a reference policy, never physical force evidence."""
from copy import deepcopy
import importlib.util
import numpy as np
import pytest
from test_spatial_load_transition import inputs
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.contact_equilibrium import skew


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.load_xyz'), \
        'height-only rank-one policy still owns the spatial command'
    from integrated_robot_navigation.load_xyz import SpatialXYZTransition
    return SpatialXYZTransition


def xyz_inputs(model):
    model,a=inputs(model);pose=a['body_pose'];q=a['joints']
    refs={f:(pose@np.r_[fk_leg(model,f,[q[f[:2]+'_'+p+'_joint'] for p in ('hip','thigh','calf')]),1.])[:3]
        for f in model.feet}
    a.pop('reference_z');a['reference_xyz']=refs;a['origins']=deepcopy(refs)
    a['allowed_z']={f:(v[2]-.01,v[2]+.01) for f,v in refs.items()}
    a['future_targets']=deepcopy(refs)
    return model,a


def test_full_response_has_six_force_directions_and_preserves_body_wrench(nav_robot_model):
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits())
    response=kernel.spatial_response(a['joints'],a['body_pose'],a['points'])
    assert response.shape==(12,12) and np.linalg.matrix_rank(response,tol=1e-7)==6
    grasp=np.hstack([np.vstack((np.eye(3),skew(a['points'][f]-a['body_pose'][:3,3]))) for f in model.feet])
    assert np.max(np.abs(grasp@response))<1e-6
    assert np.allclose(kernel.response(a['joints'],a['body_pose'],a['points']),response[:,[2,5,8,11]])


def test_step_owns_stance_xyz_but_keeps_selected_xy_fixed_and_bounded(nav_robot_model):
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits());before=deepcopy(a)
    delta=kernel.step(**a)
    assert set(delta)==set(model.feet)
    for f,d in delta.items():
        assert np.shape(d)==(3,) and np.linalg.norm(d)<=a['speed']*a['dt']+1e-10
        assert np.linalg.norm(a['reference_xyz'][f]+d-a['origins'][f])<=.01+1e-10
    assert np.allclose(delta[a['foot']][:2],0.,atol=1e-14) and delta[a['foot']][2]>=0.
    assert any(np.linalg.norm(delta[f][:2])>1e-8 for f in model.feet if f!=a['foot'])
    predicted=kernel.last_model['predicted_forces_world'][a['foot']]
    assert np.linalg.norm(predicted)<np.linalg.norm(a['forces_world'][a['foot']])
    assert kernel.last_model['scope']=='spatial_spring_prediction_not_measured_force_or_torque'
    assert kernel.last_model['command_space']=='stance_xyz'
    assert kernel.last_model['future_geometry_validated'] is True
    assert kernel.last_model.get('linear_origin_feasible') is True
    assert a['forces_world']==before['forces_world']


def test_total_vector_cap_is_not_three_independent_ten_mm_limits(nav_robot_model):
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits())
    a['origins']['fr_foot']=a['reference_xyz']['fr_foot']-np.array([.01,0.,0.])
    delta=kernel.step(**a)
    for f,d in delta.items():
        assert np.linalg.norm(a['reference_xyz'][f]+d-a['origins'][f])<=.01+1e-10


def test_unreachable_future_swing_cannot_get_a_numeric_reference(nav_robot_model):
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits())
    a['future_targets'][a['foot']][0]+=1.
    with pytest.raises(ValueError,match='geometry'):kernel.step(**a)
    assert kernel.last_model is None


def test_original_z_direction_envelope_still_bounds_xyz(nav_robot_model):
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits())
    for f in model.feet:a['allowed_z'][f]=(a['reference_xyz'][f][2],a['reference_xyz'][f][2])
    delta=kernel.step(**a)
    assert all(abs(d[2])<1e-12 for d in delta.values())


@pytest.mark.parametrize('field',['origins','reference_xyz','future_targets'])
def test_xyz_requires_complete_finite_original_geometry(nav_robot_model,field):
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits())
    a[field][model.feet[0]][0]=float('nan')
    with pytest.raises(ValueError):kernel.step(**a)


def test_xyz_worker_reuses_compiled_immutable_geometry_without_skipping_grid(nav_robot_model):
    from integrated_robot_navigation.compiled_reference import CompiledReferenceEnvelope
    model,a=xyz_inputs(nav_robot_model);kernel=api()(model,default_limits())
    assert isinstance(getattr(kernel,'geometry',None),CompiledReferenceEnvelope), \
        'actual numerical worker still repeats full URDF/FK validation per grid point'
    delta=kernel.step(**a)
    assert set(delta)==set(model.feet) and kernel.last_model['future_geometry_validated'] is True
