"""Breaks: timer-only lift, multiple swings, stale-feedback or post-stop advance."""
from dataclasses import replace
import importlib
import math

import numpy as np
import pytest

from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.support import center_of_mass, support_margin
from gait_fixture import IdealFeedback


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.gait'), 'crawl machine missing'
    return importlib.import_module('integrated_robot_navigation.gait')


def machine(model, plant):
    value = api().CrawlMachine(model, default_limits())
    value.reset(plant.state, plant.ros, plant.wall)
    return value


@pytest.mark.parametrize('missing_support', [False, True])
def test_no_lift_from_planned_com_or_missing_measured_support(nav_robot_model, missing_support):
    plant = IdealFeedback(nav_robot_model)
    if missing_support:
        data = {**plant.state.contacts.data, 'forces': (0., 30., 30., 30.),
                'touching': (False, True, True, True)}
        plant.state = replace(plant.state, contacts=replace(plant.state.contacts, data=data))
    value = machine(nav_robot_model, plant)
    for _ in range(120):
        result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
        assert result.swing_foot is None, 'without actual body/joint response no support margin was gained'
        plant.tick(follow=False)
        if missing_support:
            plant.state = replace(plant.state, contacts=replace(plant.state.contacts, data=data))


def test_one_swing_order_and_measured_support_margin_in_ideal_feedback(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    order = []
    last = None
    for _ in range(550):
        result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        if result.swing_foot is not None:
            if result.swing_foot != last:
                order.append(result.swing_foot)
                last = result.swing_foot
            stance = [p for name, p, force in zip(nav_robot_model.feet,
                plant.state.contacts.data['points'], plant.state.contacts.data['forces'])
                if name != result.swing_foot and force >= 2.]
            com = center_of_mass(nav_robot_model, plant.state.joints.data['position'], plant.pose)
            assert len(stance) >= 3 and support_margin(com, stance) >= .01-1e-9
        plant.tick(value, result)
        assert sum(not t for t in plant.state.contacts.data['touching']) <= 1
        if len(order) == 4:
            break
    assert order == ['fl_foot', 'rr_foot', 'fr_foot', 'rl_foot']


@pytest.mark.parametrize('bad', [(math.nan, 0., 0.), (.011, 0., 0.), (0., .001, 0.)])
def test_invalid_command_emits_no_new_joint_target(nav_robot_model, bad):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    result = value.advance(plant.state, bad, plant.ros, plant.wall)
    assert result.state == 'FAULT' and result.joint_targets is None


def test_feedback_expiry_never_claims_stopped_or_guesses_a_landing(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    value.request_stop(urgent=True)
    result = value.advance(plant.state, (0., 0., 0.), plant.ros+200_000_001,
                           plant.wall+200_000_001)
    assert result.state == 'FAULT' and result.joint_targets is None
    assert result.state != 'STOPPED'


def test_stop_freezes_body_advance_and_lands_before_measured_settle(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    for _ in range(200):
        result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
        plant.tick(value, result)
        if result.phase == 'SWING' and not all(plant.state.contacts.data['touching']):
            break
    else:
        pytest.fail('never reached a measured unloaded swing')
    initial = np.asarray(value.reference_body).copy()
    value.request_stop(urgent=False)
    landed_at, stopped_at = None, None
    for i in range(120):
        result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        assert np.allclose(np.asarray(value.reference_body)[:2, 3], initial[:2, 3], atol=1e-12)
        plant.tick(value, result)
        if all(plant.state.contacts.data['touching']) and landed_at is None:
            landed_at = (i+1)*.02
        if result.state == 'STOPPED':
            stopped_at = (i+1)*.02
            break
    assert landed_at is not None and landed_at <= 1.
    assert stopped_at is not None and stopped_at >= landed_at+.98


def test_inconsistent_measured_stance_latches_without_retry(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    data = {**plant.state.body.data, 'position': (0., 0., .69)}
    broken = replace(plant.state, body=replace(plant.state.body, data=data))
    result = value.advance(broken, (.001, 0., 0.), plant.ros, plant.wall)
    assert result.state == 'FAULT' and result.joint_targets is None
    recovered = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
    assert recovered.state == 'FAULT' and recovered.joint_targets is None


@pytest.mark.parametrize('failure', ['unreachable', 'gait_bound'])
def test_ik_boundary_failure_emits_no_clipped_target(nav_robot_model, monkeypatch, failure):
    module = api()
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    if failure == 'unreachable':
        def broken(*args):
            raise ValueError('unreachable injected at tested IK boundary')
    else:
        def broken(*args):
            return (.25, -.5, 1.)  # legal URDF hip, illegal footprint-bound gait hip
    monkeypatch.setattr(module, 'ik_leg', broken)
    result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
    assert result.state == 'FAULT' and result.joint_targets is None


def test_zero_velocity_lands_current_foot_without_starting_another_swing(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    for _ in range(200):
        result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
        plant.tick(value, result)
        if result.phase == 'SWING' and not all(plant.state.contacts.data['touching']):
            break
    else:
        pytest.fail('no swing')
    landed = False
    for _ in range(150):
        result = value.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        plant.tick(value, result)
        if all(plant.state.contacts.data['touching']):
            landed = True
        if landed:
            assert result.swing_foot is None or result.phase == 'TOUCHDOWN'
            assert all(plant.state.contacts.data['touching'])


@pytest.mark.parametrize('command', [(.01, 0., 0.), (-.01, 0., 0.),
                                     (0., 0., .03), (.01, 0., .03)])
def test_maximum_command_envelope_remains_finite_and_footprint_bound(nav_robot_model, command):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    for _ in range(450):
        result = value.advance(plant.state, command, plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        if result.joint_targets:
            for name, angle in result.joint_targets.items():
                part = name.split('_')[1]
                lo, hi = value.limits['gait_joint_bounds'][part]
                assert math.isfinite(angle) and lo <= angle <= hi
        plant.tick(value, result)


def test_current_support_outside_polygon_cannot_command_body_shift(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    data = {**plant.state.contacts.data, 'forces': (0., 30., 30., 30.),
            'touching': (False, True, True, True)}
    plant.state = replace(plant.state, contacts=replace(plant.state.contacts, data=data))
    value = machine(nav_robot_model, plant)
    result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
    assert result.state == 'FAULT' and result.joint_targets is None


def test_stance_slip_stops_new_targets(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    data = {**plant.state.body.data, 'position': (.021, 0., .46)}
    state = replace(plant.state, body=replace(plant.state.body, data=data))
    result = value.advance(state, (.001, 0., 0.), plant.ros, plant.wall)
    assert result.state == 'FAULT' and result.joint_targets is None and 'slip' in result.reason


def test_stop_requires_measured_speed_not_command_zero(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    value.request_stop(urgent=False)
    for _ in range(70):
        data = {**plant.state.body.data, 'linear_velocity': (.004, 0., 0.)}
        state = replace(plant.state, body=replace(plant.state.body, data=data))
        result = value.advance(state, (0., 0., 0.), plant.ros, plant.wall)
        assert result.state != 'STOPPED'
        plant.tick(value, result)


@pytest.mark.parametrize('clock', ['ros_rollback', 'wall_rollback', 'pause'])
def test_clock_faults_are_latched_without_new_targets(nav_robot_model, clock):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    ros = plant.ros-1 if clock == 'ros_rollback' else plant.ros
    wall = plant.wall-1 if clock == 'wall_rollback' else plant.wall
    if clock == 'pause':
        wall += 200_000_001
    result = value.advance(plant.state, (.001, 0., 0.), ros, wall)
    assert result.state == 'FAULT' and result.joint_targets is None
    plant.tick()
    result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
    assert result.state == 'FAULT' and result.joint_targets is None


def test_explicit_stop_never_resumes_on_nonzero_velocity(nav_robot_model):
    plant = IdealFeedback(nav_robot_model)
    value = machine(nav_robot_model, plant)
    value.request_stop(urgent=False)
    for _ in range(110):
        result = value.advance(plant.state, (.001, 0., 0.), plant.ros, plant.wall)
        plant.tick(value, result)
    assert result.state == 'STOPPED' and result.swing_foot is None
    assert np.allclose(value.reference_body[:2, 3], (0., 0.), atol=1e-12)
