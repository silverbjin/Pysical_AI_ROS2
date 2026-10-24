"""Pure reference/measurement boundary; never a native G1 success claim."""
import importlib
import math

import pytest

from integrated_robot_navigation.carry_profile import default_limits


def trajectory(*, start_z=.029, wall=10_000_000_000, deadline=20_000_000_000,limits=None):
    assert importlib.util.find_spec('integrated_robot_navigation.calibration'), 'G1-specific reference missing'
    from integrated_robot_navigation.calibration import InPlaceCalibration
    return InPlaceCalibration(start_z=start_z, rest_z=.017, baseline_z=.020,
        limits=default_limits() if limits is None else limits, ros_ns=1_000_000_000, wall_ns=wall,
        deadline_wall_ns=deadline)


def tick(value,index,*,center=.020,forces=(30.,0.,30.,30.),capture=None):
    ros = 1_000_000_000+index*20_000_000
    return value.advance(ros_ns=ros,wall_ns=10_000_000_000+index*20_000_000,
        center_z=center,forces=forces,capture_ns=ros if capture is None else capture)


def test_timer_and_command_height_cannot_replace_three_unique_measured_lifts():
    value = trajectory()
    for index in range(1,5):
        assert tick(value,index,center=.0259).phase == 'SWING'
    assert tick(value,5,center=.0261).phase == 'SWING'
    for index in range(6,10):
        assert tick(value,index,center=.0261,capture=1_100_000_000).phase == 'SWING'
    assert tick(value,10,center=.0261).phase == 'SWING'
    result = tick(value,11,center=.0261)
    assert result.phase == 'TOUCHDOWN' and not result.complete
    assert value.snapshot()['lift_captures'] == [1_100_000_000,1_200_000_000,1_220_000_000]


def test_loaded_or_interrupted_lift_cannot_accumulate_success():
    value = trajectory()
    tick(value,1,center=.027)
    tick(value,2,center=.027,forces=(30.,2.1,30.,30.))
    assert tick(value,3,center=.027).phase == 'SWING'
    assert tick(value,4,center=.027).phase == 'SWING'
    assert tick(value,5,center=.027).phase == 'TOUCHDOWN'


def test_reference_speed_envelope_and_real_landing_not_timer_completion():
    value = trajectory()
    previous = .029
    for index in range(1,27):
        result = tick(value,index,center=.027 if index<=3 else .030)
        assert abs(result.z-previous)/.02 <= .020000001
        assert .017 <= result.z <= .040
        assert not result.complete
        previous = result.z
    assert result.phase == 'TOUCHDOWN'
    for index in range(27,60):
        result = tick(value,index,center=.020,forces=(30.,3.,30.,30.))
        assert abs(result.z-previous)/.02 <= .020000001, 'approved G1 planned return stays bounded under load'
        assert not result.complete, 'sub-margin load is not restored stable support'
        previous = result.z
    assert result.z == pytest.approx(.017,abs=1e-12), 'reference endpoint precedes loaded completion'
    assert tick(value,60,center=.020,forces=(30.,4.1,30.,30.)).complete is False
    assert tick(value,61,center=.020,forces=(30.,4.1,30.,30.)).complete is False
    landed = tick(value,62,center=.020,forces=(30.,4.1,30.,30.))
    assert landed.complete and landed.phase == 'STAND'
    assert value.snapshot()['scope'] == 'candidate_requires_owner_measured_stand_settle'


def test_airborne_return_is_not_mistaken_for_loaded_seek_by_height_alone():
    value=trajectory()
    for index in range(1,4): tick(value,index,center=.027)
    previous=value.z
    speeds=[]
    for index in range(4,15):
        result=tick(value,index,center=.0215,forces=(30.,0.,30.,30.))
        speeds.append((previous-result.z)/.02)
        assert not result.complete and result.phase=='TOUCHDOWN'
        assert .017<=result.z<=.040
        previous=result.z
    assert max(speeds)>.01, 'airborne proximity incorrectly selects the2mm/s loaded-contact seek'
    assert max(speeds)<=.020000001
    result=tick(value,15,center=.020,forces=(30.,2.5,30.,30.))
    assert 0<previous-result.z<=.02*.02000001, 'G1 planned return is not a separate contact-seek trajectory'
    assert not result.complete, 'the original4N/unique-capture/owner-settle checks remain'


def test_duplicate_landing_or_other_foot_unloaded_is_not_completion():
    value = trajectory()
    for index in range(1,4): tick(value,index,center=.027)
    for index in range(4,60):
        assert not tick(value,index,center=.020,forces=(30.,0.,30.,30.)).complete
    assert value.z == pytest.approx(.017,abs=1e-12)
    tick(value,60,center=.020,forces=(30.,5.,30.,30.))
    for index in range(61,65):
        assert not tick(value,index,center=.020,forces=(30.,5.,30.,30.),capture=2_200_000_000).complete
    assert not tick(value,65,center=.020,forces=(30.,5.,0.,30.)).complete
    for index in (66,67):
        assert not tick(value,index,center=.020,forces=(30.,5.,30.,30.)).complete
    assert tick(value,68,center=.020,forces=(30.,5.,30.,30.)).complete


@pytest.mark.parametrize('kind',['rollback','deadline','future_capture','nonfinite'])
def test_invalid_time_or_measurement_is_sticky_and_never_restarts(kind):
    value = trajectory()
    with pytest.raises(ValueError):
        value.advance(ros_ns=999_000_000 if kind=='rollback' else 1_020_000_000,
            wall_ns=20_000_000_000 if kind=='deadline' else 10_020_000_000,
            center_z=math.nan if kind=='nonfinite' else .027,forces=(30.,0.,30.,30.),
            capture_ns=2_000_000_000 if kind=='future_capture' else 1_000_000_000)
    with pytest.raises(ValueError): tick(value,2,center=.027)


def test_missing_measured_lift_hits_envelope_and_fails_not_an_extra_trial():
    value = trajectory(start_z=.0399)
    with pytest.raises(ValueError,match='lift.*envelope'):
        for index in range(1,30): tick(value,index,center=.020)
    assert value.snapshot()['fault']


def test_deadline_is_original_request_budget_not_new_swing_budget():
    value = trajectory(wall=19_950_000_000,deadline=20_000_000_000)
    result = value.advance(ros_ns=1_020_000_000,wall_ns=19_970_000_000,
        center_z=.027,forces=(30.,0.,30.,30.),capture_ns=1_020_000_000)
    assert not result.complete
    snapshot = value.snapshot()
    assert snapshot['last_update_wall_ns']==19_970_000_000
    assert snapshot['remaining_wall_ns']==30_000_000
    with pytest.raises(ValueError,match='deadline'):
        value.advance(ros_ns=1_040_000_000,wall_ns=20_000_000_000,
            center_z=.027,forces=(30.,0.,30.,30.),capture_ns=1_040_000_000)


def test_tighter_configured_speed_is_not_overridden_by_default_unload_rate():
    limits = default_limits()
    limits['max_swing_speed_mps'] = .001
    value = trajectory(limits=limits)
    previous = .029
    for index in range(1,4):
        result = tick(value,index,center=.027)
        assert abs(result.z-previous)/.02<=.001000001
        previous = result.z
