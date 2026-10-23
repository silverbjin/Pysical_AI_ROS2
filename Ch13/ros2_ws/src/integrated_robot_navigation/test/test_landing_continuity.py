"""Break: timer-only descent pushes a loaded foot, then snaps its reference.

Ideal feedback tests the command boundary, not native landing dynamics.
"""
from dataclasses import replace
import numpy as np
import pytest

from gait_fixture import IdealFeedback
from test_gait import machine
from integrated_robot_navigation.leg_kinematics import ik_leg


def descending_swing(model):
    plant = IdealFeedback(model)
    value = machine(model, plant)
    value.request_contact_calibration()
    for _ in range(450):
        result = value.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
        assert result.state != 'FAULT', result.reason
        if (result.phase == 'SWING' and
                (plant.ros-value._phase_start)/1e9 >= .7*value._swing_duration):
            return plant, value, result
        plant.tick(value, result)
    pytest.fail('descending single-foot calibration not reached')


def contact(plant, loaded):
    data = plant.state.contacts.data
    forces = list(data['forces'])
    forces[1] = 5. if loaded else 0.  # model order FR, FL, RR, RL
    plant.state = replace(plant.state, contacts=replace(plant.state.contacts,
        data={**data, 'forces': tuple(forces), 'touching': tuple(f >= 2. for f in forces)}))


def test_measured_early_contact_stops_descent_without_waiting_for_swing_timer(nav_robot_model):
    plant, value, previous = descending_swing(nav_robot_model)
    before = value._targets['fl_foot'].copy()
    contact(plant, True)
    current = value.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
    assert current.phase == 'TOUCHDOWN', 'actual landing must preempt timed downward swing'
    assert np.allclose(value._targets['fl_foot'], before, atol=1e-12)
    assert np.allclose(list(current.joint_targets.values()), list(previous.joint_targets.values()), atol=1e-12)


@pytest.mark.parametrize('case', ['measured_compliance', 'contact_rebound'])
def test_touchdown_never_rewinds_command_to_floor_or_measured_center(nav_robot_model, case):
    plant, value, previous = descending_swing(nav_robot_model)
    # Enter the existing touchdown branch directly to isolate the second defect
    # from the early-contact transition test above.
    value.phase, value._phase_start = 'TOUCHDOWN', plant.ros
    before = value._targets['fl_foot'].copy()
    if case == 'measured_compliance':
        local = (np.linalg.inv(value.reference_body) @ np.r_[before, 1.])[:3]
        local[2] -= .002
        q = dict(plant.state.joints.data['position'])
        angles = ik_leg(nav_robot_model, 'fl_foot', local,
                        tuple(q['fl_'+part+'_joint'] for part in ('hip', 'thigh', 'calf')))
        q.update(zip(('fl_hip_joint', 'fl_thigh_joint', 'fl_calf_joint'), angles))
        plant.state = replace(plant.state, joints=replace(plant.state.joints,
            data={**plant.state.joints.data, 'position': q}))
    iterations = 14 if case == 'measured_compliance' else 1
    for _ in range(iterations):
        plant.tick(follow=False)
        contact(plant, case == 'measured_compliance')
        current = value.advance(plant.state, (0., 0., 0.), plant.ros, plant.wall)
        assert current.state != 'FAULT', current.reason
    if case == 'measured_compliance':
        assert current.phase == 'SETTLE'
        assert np.allclose(value._targets['fl_foot'], before, atol=1e-12), \
            'encoder compliance is not permission for a new downward position step'
    else:
        assert 0 <= before[2]-value._targets['fl_foot'][2] <= .002*.02+1e-12, \
            'lost contact permits only bounded slow search, never a jump to old floor'
