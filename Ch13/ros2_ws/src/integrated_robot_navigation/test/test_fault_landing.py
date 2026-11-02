"""Explicit safe landing is not reactivation of a latched motion fault."""
from copy import deepcopy
import numpy as np
from gait_fixture import IdealFeedback
from test_gait import machine
from test_calibration_clock_progress import sample_at


def unload_fault(model):
    plant=IdealFeedback(model);value=machine(model,plant)
    for _ in range(500):
        result=value.advance(plant.state,(.01,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(value,result)
        if value.phase=='SHIFT' and value._unload_start is not None:break
    else:raise AssertionError('unload stage not reached')
    foot=value.swing_foot;value._targets[foot][2]=value.floor[foot]+.0075
    plant.tick(value,value._result(value._solve(plant.state.joints.data['position'],True)))
    result=value._fail('measured unload timeout')
    assert result.state=='FAULT' and result.joint_targets is None
    return value,plant,foot


def test_explicit_stop_after_contact_deadline_lands_only_the_known_foot_and_keeps_fault(nav_robot_model):
    value,plant,foot=unload_fault(nav_robot_model)
    held=value.reference_body.copy();generation=value.generation
    before=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
    assert before.state=='FAULT' and before.joint_targets is None
    value.request_stop(urgent=True);previous=value._targets[foot].copy()
    for _ in range(150):
        result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall,reference_permitted=False)
        assert result.state not in ('CRAWL','STAND')
        assert np.array_equal(value.reference_body,held)
        assert np.linalg.norm(value._targets[foot]-previous)/.02<=value.limits['max_swing_speed_mps']+1e-9
        previous=value._targets[foot].copy()
        plant.tick(value,result)
        if result.state=='STOPPED':break
    assert result.state=='STOPPED','explicit stop could not land the known unloaded foot'
    assert all(plant.state.contacts.data['touching'])
    assert result.reason=='measured unload timeout' and result.generation==generation
    result=value.advance(plant.state,(.01,0.,0.),plant.ros,plant.wall)
    assert result.state=='STOPPED' and result.reason=='measured unload timeout'


def test_contact_fault_cannot_land_with_stale_feedback_or_recover_on_later_input(nav_robot_model):
    value,plant,_=unload_fault(nav_robot_model);value.request_stop(urgent=True)
    r,w=value._last_ros+200_000_001,value._last_wall+200_000_001
    result=value.advance(plant.state,(0.,0.,0.),r,w)
    assert result.state=='FAULT' and result.joint_targets is None
    result=value.advance(sample_at(plant.state,r+20_000_000,w+20_000_000),
        (0.,0.,0.),r+20_000_000,w+20_000_000)
    assert result.state=='FAULT' and result.joint_targets is None


def test_support_or_owner_fault_never_authorizes_fault_landing(nav_robot_model):
    value,plant,_=unload_fault(nav_robot_model)
    for reason in ('current measured support lost','owner:legs'):
        other=deepcopy(value);other._fail(reason);other.request_stop(urgent=True)
        result=other.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state=='FAULT' and result.joint_targets is None
