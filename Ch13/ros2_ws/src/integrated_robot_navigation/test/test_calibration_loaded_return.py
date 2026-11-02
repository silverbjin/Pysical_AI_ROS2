"""49324eec: loaded return, fixed endpoint/deadline; not physical acceptance."""
import pytest
from integrated_robot_navigation.calibration import InPlaceCalibration
from integrated_robot_navigation.carry_profile import default_limits


def test_contact_during_return_brakes_then_finishes_same_preload_within_original_budget():
    request_ros=26757999999
    request_wall=3145750468071
    start_ros=31071999999
    start_wall=request_wall+(start_ros-request_ros)
    limits=default_limits()
    profile=InPlaceCalibration(start_z=.031800535064822624,
        rest_z=.017607735064822827,baseline_z=.01871437788833158,limits=limits,
        ros_ns=start_ros,wall_ns=start_wall,deadline_wall_ns=request_wall+10_000_000_000)
    profile.phase='TOUCHDOWN';profile.velocity=.02
    contact_ros=32478000000
    last_velocity=profile.velocity
    loaded_maximum=0.
    for i in range(1,300):
        now=start_ros+i*20_000_000
        loaded=now>=contact_ros
        step=profile.advance(ros_ns=now,wall_ns=start_wall+i*20_000_000,
            center_z=profile.baseline_z,forces=(30.,10.49 if loaded else 0.,30.,30.),capture_ns=now)
        assert abs(profile.velocity-last_velocity)/.02<=.20000001
        last_velocity=profile.velocity
        if now>=contact_ros+400_000_000:
            loaded_maximum=max(loaded_maximum,-profile.velocity)
        if step.complete:break
    assert loaded_maximum<=2*limits['unload_speed_mps']+1e-10, \
        'the planned reference still cruises10mm/s after a loaded touchdown'
    assert step.complete and step.z==pytest.approx(profile.rest_z)
    assert start_wall+i*20_000_000+1_000_000_000<profile.deadline
    snapshot=profile.snapshot()
    assert snapshot['loaded_contact']['capture_ns']>=contact_ros
    assert snapshot['loaded_brake']['complete']
    assert snapshot['previous_return_plan']['nominal_speed_mps']==.01
    assert snapshot['return_plan']['nominal_speed_mps']<=.004


def test_loaded_plan_cannot_consume_the_original_owner_settle_budget():
    value=InPlaceCalibration(start_z=.030,rest_z=.017,baseline_z=.020,
        limits=default_limits(),ros_ns=1_000_000_000,wall_ns=19_500_000_000,
        deadline_wall_ns=20_000_000_000)
    value.phase='TOUCHDOWN';value.velocity=0.
    with pytest.raises(ValueError,match='original wall settle budget'):
        value.advance(ros_ns=1_020_000_000,wall_ns=19_520_000_000,
            center_z=.020,forces=(30.,5.,30.,30.),capture_ns=1_020_000_000)
    assert value.deadline==20_000_000_000 and value.fault
    with pytest.raises(ValueError):
        value.advance(ros_ns=1_040_000_000,wall_ns=19_540_000_000,
            center_z=.020,forces=(30.,5.,30.,30.),capture_ns=1_040_000_000)
