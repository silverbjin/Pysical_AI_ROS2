"""Spatial response/optimization invariants; never a simulator acceptance."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from test_stance_load_transfer import helper
from integrated_robot_navigation.contact_equilibrium import static_support,skew


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.load_transition'), \
        'spatial, effort-bounded position load transition missing'
    from integrated_robot_navigation.load_transition import SpatialLoadTransition
    return SpatialLoadTransition


def inputs(model):
    model=helper(model).model;plant=IdealFeedback(model);plant.tick()
    points=dict(zip(model.feet,plant.state.contacts.data['points']));q=plant.state.joints.data['position']
    current=static_support(model,q,plant.pose,points,model.feet)
    target=static_support(model,q,plant.pose,points,tuple(f for f in model.feet if f!='rr_foot'),min_force=0.)
    return model,dict(foot='rr_foot',joints=q,body_pose=plant.pose,points=points,
        forces_world=current['forces_world'],target_forces=target['forces_world'],
        reference_z={f:.02 for f in model.feet},origins={f:.02 for f in model.feet},
        allowed_z={f:(.01,.03) for f in model.feet},dt=.02,speed=.002,min_force=2.)


def test_height_response_preserves_all_six_net_wrench_components(nav_robot_model):
    model,args=inputs(nav_robot_model);value=api()(model)
    response=value.response(args['joints'],args['body_pose'],args['points'])
    assert response.shape==(12,4)
    grasp=np.hstack([np.vstack((np.eye(3),skew(np.asarray(args['points'][f])-args['body_pose'][:3,3]))) for f in model.feet])
    assert np.max(np.abs(grasp@response))<1e-6
    assert np.max(np.abs(response[[0,1,3,4,6,7,9,10]]))>1., 'horizontal coupling was discarded'


def test_bounded_step_reduces_selected_load_without_inventing_measured_forces(nav_robot_model):
    model,args=inputs(nav_robot_model);value=api()(model)
    original={f:list(v) for f,v in args['forces_world'].items()}
    delta=value.step(**args)
    assert set(delta)==set(model.feet)
    assert all(abs(d)<=.002*.02+1e-12 for d in delta.values())
    assert delta['rr_foot']>=0.
    assert value.last_model['predicted_forces_world']['rr_foot'][2]<original['rr_foot'][2]
    assert args['forces_world']==original
    assert value.last_model['scope']=='spatial_spring_prediction_not_measured_force_or_torque'


def test_reference_cap_is_an_optimizer_bound_not_hidden_integrator_windup(nav_robot_model):
    model,args=inputs(nav_robot_model);value=api()(model)
    args['reference_z']={f:.03 for f in model.feet}
    delta=value.step(**args)
    assert all(d<=1e-12 for d in delta.values())
    assert delta['rr_foot']==pytest.approx(0.,abs=1e-12)
    again=value.step(**args)
    assert again==pytest.approx(delta), 'an unapplied hidden reference accumulated'


def test_feedback_that_cannot_meet_motor_constraints_cannot_emit_a_reference(nav_robot_model):
    model,args=inputs(nav_robot_model);value=api()(model)
    args['forces_world']={f:[0.,0.,100000.] for f in model.feet}
    with pytest.raises(ValueError,match='transition optimization'):
        value.step(**args)


def test_native_servo_reference_error_is_not_hidden_by_static_contact_torque(nav_robot_model):
    model,args=inputs(nav_robot_model);value=api()(model)
    command=dict(args['joints']);command['fl_calf_joint']+=.2
    with pytest.raises(ValueError,match='transition optimization'):
        value.step(**args,command_joints=command,reference_pose=args['body_pose'])


def test_late_post_solver_validation_cannot_publish_a_reference(nav_robot_model,monkeypatch):
    from types import SimpleNamespace
    from integrated_robot_navigation import load_transition as module
    model,args=inputs(nav_robot_model);value=api()(model)
    original=module.minimize;clock=module.time.perf_counter_ns;finished=[False]
    def solve(*a,**k):
        result=original(*a,**k);finished[0]=True;return result
    monkeypatch.setattr(module,'minimize',solve)
    monkeypatch.setattr(module,'time',SimpleNamespace(
        perf_counter_ns=lambda:clock()+(20_000_000 if finished[0] else 0)))
    with pytest.raises(ValueError,match='transition optimization time budget'):value.step(**args)
    assert value.last_model is None


def test_actual_first_transition_keeps_the_preoptimization_mathematical_result():
    from integrated_robot_navigation.model import compile_model
    data=json.loads((Path(__file__).parent/'fixtures/native_26a3_spatial_budget.json').read_text())
    model=compile_model(data['urdf']);value=api()(model)
    try:result=value.step(**data['args'])
    except ValueError:
        # Keep the original deadline failure and expose wall/CPU stages;
        # a later passing replay must not erase this trial's rejection.
        print(json.dumps(value.last_attempt,sort_keys=True))
        raise
    assert result==pytest.approx(data['expected_delta'],abs=1e-9)
    assert all(abs(d)<=data['args']['dt']*.002+1e-12 for d in result.values())


@pytest.mark.parametrize('change',[dict(dt=-.1),dict(dt=.21),dict(speed=0.),dict(forces_world={}),
    dict(allowed_z={}),dict(forces_world={'fr_foot':[float('nan'),0.,1.]})])
def test_invalid_spatial_inputs_fail_closed(nav_robot_model,change):
    model,args=inputs(nav_robot_model);value=api()(model);args.update(change)
    with pytest.raises(ValueError):value.step(**args)
