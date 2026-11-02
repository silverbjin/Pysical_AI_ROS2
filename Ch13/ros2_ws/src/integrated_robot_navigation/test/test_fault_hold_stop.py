"""A stopped fault remains a fault; the hold observer must never move a leg.

Reproduces the SHIFT-timeout shutdown dead end in cbe25816/cb59e4f3.
Ideal feedback checks the protocol, never native physical acceptance.
"""
from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest

from test_crawl_shift_clock_progress import shifting
from test_calibration_clock_progress import sample_at


REASON='shift timeout; measured support/settle not gained'


def test_loaded_unload_height_fault_only_confirms_read_only_stop_after_explicit_request(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    value.swing_foot='fr_foot';value._unload_start=plant.ros
    value._targets['fr_foot'][2]+=value.limits['max_unload_height_m']
    reason='measured unload height bound reached'
    value._fail(reason);plant.tick(follow=False)
    held=deepcopy(value._targets);generation=value.generation
    for index in range(55):tick(value,plant,index)
    assert not value.fault_stop_confirmed,'fault alone became a stop acknowledgement'
    value.request_stop(urgent=True)
    for index in range(55):
        result=tick(value,plant,index)
        assert result.state=='FAULT' and result.reason==reason and result.generation==generation
        assert result.joint_targets is None
        assert all(np.array_equal(point,value._targets[name]) for name,point in held.items())
    assert value.fault_stop_confirmed, 'fresh loaded height-limit fault never acknowledged measured stop'


def test_height_fault_with_missing_support_never_recovers_on_later_input(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    value.swing_foot='fr_foot';value._unload_start=plant.ros
    value._fail('measured unload height bound reached');value.request_stop(urgent=True)
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    bundle=sample_at(plant.state,ros,wall)
    bundle=replace(bundle,contacts=replace(bundle.contacts,data={**bundle.contacts.data,
        'forces':(0.,30.,30.,30.),'touching':(False,True,True,True)}))
    result=value.advance(bundle,(0.,0.,0.),ros,wall)
    assert result.state=='FAULT' and result.joint_targets is None
    for index in range(60):tick(value,plant,index)
    assert not value.fault_stop_confirmed


def held_fault(model):
    value,plant=shifting(model,(.01,0.,0.))
    assert value.phase=='SHIFT' and value.swing_foot is None
    value._fail(REASON)
    plant.tick(follow=False)  # a held ideal plant stops; this is not engine proof
    return value,plant


def tick(value,plant,index,**changes):
    ros=value._last_ros+20_000_000;wall=value._last_wall+20_000_000
    bundle=sample_at(plant.state,ros,wall)
    if changes:
        bundle=replace(bundle,body=replace(bundle.body,data={**bundle.body.data,**changes}))
    return value.advance(bundle,(0.,0.,0.),ros,wall,reference_permitted=False)


def test_shift_timeout_stop_confirms_fresh_settle_without_emitting_targets_or_clearing_fault(nav_robot_model):
    value,plant=held_fault(nav_robot_model)
    held=value.reference_body.copy();targets=deepcopy(value._targets);generation=value.generation
    value.request_stop(urgent=True)
    for index in range(55):
        result=tick(value,plant,index)
        assert result.state=='FAULT' and result.reason==REASON and result.generation==generation
        assert result.joint_targets is None, 'fault observation issued a motor reference'
        assert np.array_equal(value.reference_body,held)
        assert all(np.array_equal(point,value._targets[name]) for name,point in targets.items())
        if index<50:assert not getattr(value,'fault_stop_confirmed',False)
    assert getattr(value,'fault_stop_confirmed',False), (value._fault_hold_observation,
        value._fault_settle_origin,value._fault_capture_count,plant.state.body.data)
    result=value.advance(sample_at(plant.state,value._last_ros,value._last_wall),(.01,0.,0.),
        value._last_ros,value._last_wall)
    assert result.state=='FAULT' and result.joint_targets is None


def test_no_stop_request_and_moving_body_cannot_count_as_settled(nav_robot_model):
    value,plant=held_fault(nav_robot_model)
    for index in range(60):tick(value,plant,index)
    assert not getattr(value,'fault_stop_confirmed',False)
    value.request_stop(urgent=True)
    for index in range(60):tick(value,plant,index,linear_velocity=(.004,0.,0.))
    assert not getattr(value,'fault_stop_confirmed',False)


@pytest.mark.parametrize('invalid', ['stale','support','owner'])
def test_invalid_fault_stop_observation_never_resumes_on_later_fresh_feedback(nav_robot_model,invalid):
    value,plant=held_fault(nav_robot_model);value.request_stop(urgent=True)
    for index in range(55):tick(value,plant,index)
    assert getattr(value,'fault_stop_confirmed',False)
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    bundle=sample_at(plant.state,ros,wall)
    if invalid=='stale':bundle=replace(bundle,body=replace(bundle.body,received_ns=wall-200_000_001))
    elif invalid=='support':
        bundle=replace(bundle,contacts=replace(bundle.contacts,data={**bundle.contacts.data,
            'forces':(0.,30.,30.,30.),'touching':(False,True,True,True)}))
    else:value._fail('owner:legs')
    result=value.advance(bundle,(0.,0.,0.),ros,wall)
    assert result.state=='FAULT' and result.joint_targets is None
    assert not getattr(value,'fault_stop_confirmed',False)
    for index in range(65):tick(value,plant,index)
    assert not getattr(value,'fault_stop_confirmed',False), 'invalidated fault observation recovered automatically'
