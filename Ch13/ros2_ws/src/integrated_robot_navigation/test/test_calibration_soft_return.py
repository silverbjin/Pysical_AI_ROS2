"""Recorded reference impact budget; this is NOT a physical carry success."""
import json
from pathlib import Path
import pytest
from integrated_robot_navigation.calibration import InPlaceCalibration
from integrated_robot_navigation.carry_profile import default_limits


def test_recorded_g1_return_halves_downward_speed_without_extending_wall_deadline():
    record=json.loads((Path(__file__).parent/'fixtures/native_d3e_calibration_impact.json').read_text())
    original=record['vertical'];brake=original['return_brake'];request=record['request']
    # The actual fault was fresh measured gripper motion, not stale feedback.
    fault=record['first_fault'];sample=fault['selected_joint_sample']
    assert (fault['ros_ns']-sample['stamp_ns'])==6_000_000
    assert abs(sample['data']['velocity']['gripper_left_joint'])>.005
    assert original['return_plan']['peak_mps']==.02
    wall=request['wall_ns']+(brake['start_ros_ns']-request['ros_ns'])
    profile=InPlaceCalibration(start_z=brake['start_z'],rest_z=original['rest_z'],
        baseline_z=original['baseline_z'],limits=default_limits(),ros_ns=brake['start_ros_ns'],
        wall_ns=wall,deadline_wall_ns=request['deadline_wall_ns'])
    profile.phase='TOUCHDOWN';profile.velocity=brake['start_velocity']
    previous_velocity=profile.velocity;peak_down=0.;peak_down_accel=0.
    for index in range(1,300):
        now=brake['start_ros_ns']+index*20_000_000
        result=profile.advance(ros_ns=now,wall_ns=wall+index*20_000_000,
            center_z=original['baseline_z'],forces=(30.,5.,30.,30.),capture_ns=now)
        peak_down=max(peak_down,-profile.velocity)
        if previous_velocity<=0 and profile.velocity<=0:
            peak_down_accel=max(peak_down_accel,abs(profile.velocity-previous_velocity)/.02)
        previous_velocity=profile.velocity
        if result.complete:break
    assert peak_down<=.010000001,'planned descent still reaches the impact trace20mm/s'
    assert peak_down_accel<=.10000001
    assert result.complete and result.z==pytest.approx(original['rest_z'])
    assert wall+index*20_000_000+1_000_000_000<request['deadline_wall_ns'], \
        'reference must leave the existing full wall settle within the original10seconds'
