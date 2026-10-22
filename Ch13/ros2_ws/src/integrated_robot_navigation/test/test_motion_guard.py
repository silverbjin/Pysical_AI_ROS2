"""Breaks: smoother masking raw loss, silent rearming, old generation/owner."""
from dataclasses import replace
import importlib

import pytest
from integrated_robot_navigation.carry_profile import default_limits
from guard_fixture import bundle, command, CARRY, OWNERS


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.motion_guard'), 'motion guard missing'
    return importlib.import_module('integrated_robot_navigation.motion_guard')


def armed(model):
    guard = api().MotionGuard(model, default_limits(), CARRY)
    guard.observe_owners({name: 1 for name in OWNERS})
    assert guard.set_mode('CRAWL')[0]
    return guard


def test_raw_loss_latches_even_when_smoother_and_sensors_are_fresh(nav_robot_model):
    model = nav_robot_model
    guard = armed(model)
    raw = command()
    assert guard.evaluate(bundle(model), raw, command(), 1_000_000_000, 10_000_000_000) == (
        (.006, 0., .01), '')
    output, reason = guard.evaluate(bundle(model, wall=10_200_000_001), raw,
        command(wall=10_200_000_001), 1_000_000_000, 10_200_000_001)
    assert output == (0., 0., 0.) and reason == 'raw:wall_age'
    output, reason = guard.evaluate(bundle(model, wall=10_210_000_000),
        command(wall=10_210_000_000), command(wall=10_210_000_000), 1_000_000_000, 10_210_000_000)
    assert output == (0., 0., 0.) and reason == 'raw:wall_age'
    assert not guard.set_mode('CRAWL')[0]


def test_explicit_reset_changes_generation_but_does_not_enable_motion(nav_robot_model):
    model = nav_robot_model
    guard = armed(model)
    guard.evaluate(bundle(model), None, command(), 1_000_000_000, 10_000_000_000)
    assert guard.set_mode('RESET') == (True, '')
    assert guard.generation == 1 and guard.mode == 'HOLD'
    assert guard.set_mode('CRAWL')[0]
    output, reason = guard.evaluate(bundle(model, generation=1), command(), command(),
                                   1_000_000_000, 10_000_000_000)
    assert output == (0., 0., 0.) and reason == 'raw:epoch'


@pytest.mark.parametrize('fault', ['carry', 'scan', 'joint', 'body', 'collision', 'owner', 'limit'])
def test_measured_faults_zero_without_smoother_ramp(nav_robot_model, fault):
    model = nav_robot_model
    guard = armed(model)
    state, raw, smooth = bundle(model), command(), command()
    if fault == 'carry':
        state = replace(state, carry=replace(state.carry, data={**state.carry.data, 'ready': False}))
    elif fault == 'scan':
        state = replace(state, scan=replace(state.scan, received_ns=9_600_000_000))
    elif fault == 'joint':
        data = {**state.joints.data, 'position': {**state.joints.data['position'], 'arm_joint_2': 1.24}}
        state = replace(state, joints=replace(state.joints, data=data))
    elif fault == 'body':
        state = replace(state, body=replace(state.body, data={**state.body.data, 'position': (0., 0., .2)}))
    elif fault == 'collision':
        state = replace(state, contacts=replace(state.contacts, data={**state.contacts.data,
                                                                      'unexpected_contacts': 1}))
    elif fault == 'owner':
        guard.observe_owners({name: (2 if name == 'raw' else 1) for name in OWNERS})
    elif fault == 'limit':
        smooth = replace(smooth, data=(.011, 0., 0.))
    output, reason = guard.evaluate(state, raw, smooth, 1_000_000_000, 10_000_000_000)
    assert output == (0., 0., 0.) and reason


def test_clock_rollback_requires_restart_not_a_reset(nav_robot_model):
    model = nav_robot_model
    guard = armed(model)
    guard.evaluate(bundle(model), command(), command(), 1_000_000_000, 10_000_000_000)
    output, reason = guard.evaluate(bundle(model, ros=900_000_000, wall=10_010_000_000),
        command(ros=900_000_000, wall=10_010_000_000), command(ros=900_000_000, wall=10_010_000_000),
        900_000_000, 10_010_000_000)
    assert output == (0., 0., 0.) and reason == 'clock_rollback'
    assert not guard.set_mode('RESET')[0]


def test_malformed_command_payload_fails_closed_not_an_exception(nav_robot_model):
    guard = armed(nav_robot_model)
    value, reason = guard.evaluate(bundle(nav_robot_model),
        replace(command(), data={'x': .006, 'y': 0., 'yaw': .01}), command(),
        1_000_000_000, 10_000_000_000)
    assert value == (0., 0., 0.) and reason
