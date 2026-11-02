"""Keep the measured MuJoCo impact fix out of Gazebo's proven G1 budget.

Recorded entry and contact times are a reference-only discriminator. Replaying
them cannot predict changed physical contact, carry stability or engine success.
"""
import json
from pathlib import Path

import pytest

from integrated_robot_navigation.calibration import InPlaceCalibration
from integrated_robot_navigation.carry_profile import default_limits


def replay(policy=None):
    data=json.loads((Path(__file__).parent/'fixtures/native_c1e_gazebo_return_budget.json').read_text())
    calibration=data['calibration'];vertical=calibration['vertical']
    touchdown=vertical['transitions'][1];brake=vertical['return_brake']
    contact=vertical['loaded_contact']
    start_ros=brake['start_ros_ns']
    start_wall=touchdown['wall_ns']-(touchdown['ros_ns']-start_ros)
    options={} if policy is None else dict(return_policy=policy)
    value=InPlaceCalibration(start_z=brake['start_z'],rest_z=vertical['rest_z'],
        baseline_z=vertical['baseline_z'],limits=default_limits(),ros_ns=start_ros,
        wall_ns=start_wall,deadline_wall_ns=calibration['request']['deadline_wall_ns'],**options)
    value.phase='TOUCHDOWN';value.velocity=brake['start_velocity']
    ratio=(contact['wall_ns']-touchdown['wall_ns'])/(contact['ros_ns']-touchdown['ros_ns'])
    previous_z,previous_v=value.z,value.velocity
    for index in range(250):
        now=touchdown['ros_ns']+index*20_000_000
        wall=touchdown['wall_ns']+round((now-touchdown['ros_ns'])*ratio)
        dt=(now-value.last_ros)/1e9
        loaded=now>=contact['ros_ns']
        result=value.advance(ros_ns=now,wall_ns=wall,center_z=vertical['baseline_z'],
            forces=(30.,5. if loaded else 0.,30.,30.),capture_ns=now)
        assert abs(result.z-previous_z)<=.020000001*dt
        assert abs(value.velocity-previous_v)<=.20000001*dt
        previous_z,previous_v=value.z,value.velocity
        if result.complete:return value,result
    pytest.fail('reference-only trajectory never completed')


def test_recorded_gazebo_boundary_reproduces_common_loaded_return_budget_fault():
    with pytest.raises(ValueError,match='loaded return leaves no original wall settle budget'):
        replay()


def test_explicit_gazebo_return_keeps_preload_speed_force_capture_and_original_wall_budget():
    value,result=replay('bounded_preload')
    assert result.complete and result.z==value.rest_z and value.velocity==0.
    assert len(value.landing_captures)==3
    assert value.last_wall+1_000_000_000<value.deadline
    assert value.snapshot()['return_policy']=='bounded_preload'
    assert value.loaded_brake is None


def test_unknown_return_policy_is_rejected_without_a_reference_fallback():
    with pytest.raises(ValueError,match='return policy'):
        replay('unknown')
