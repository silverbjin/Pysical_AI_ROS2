"""G1-only full-speed return: same endpoint/caps, continuous acceleration."""
import numpy as np
import pytest
from integrated_robot_navigation.calibration import InPlaceCalibration
from integrated_robot_navigation.carry_profile import default_limits


def value():
    x=InPlaceCalibration(start_z=.0365422433542334,rest_z=.01670515763223346,
        baseline_z=.019949707139506723,limits=default_limits(),ros_ns=0,wall_ns=0,
        deadline_wall_ns=10_000_000_000,return_policy='bounded_preload_smooth')
    x.phase='TOUCHDOWN';x.velocity=0.
    return x


def test_real_failed_return_distance_keeps_rate_acceleration_and_smooth_terminal():
    x=value();v=[];z=[];dt=.001
    for i in range(1,1601):
        x._planned_return(i*1_000_000,dt);v.append(x.velocity);z.append(x.z)
    a=np.diff(v)/dt;jerk=np.diff(a)/dt
    assert max(abs(np.array(v)))<=.020000001
    assert max(abs(a))<=.200001
    assert max(abs(jerk))<=3.4  # same existing quintic velocity jerk envelope
    assert max(abs(np.diff(z)/dt))<=.020000001
    assert min(z)>=x.rest_z-1e-12
    assert z[-1]==x.rest_z and v[-1]==0.
    assert x.return_plan['profile']=='quintic_velocity'
    assert x.return_plan['duration_s']<1.20
    # End acceleration decays smoothly; the final stationary point cannot
    # inherit the legacy trapezoid's abrupt .2 -> 0 acceleration change.
    end=int(np.flatnonzero(np.array(z)==x.rest_z)[0])
    assert abs(a[end-1])<.001


def test_original_wall_deadline_and_measured_landing_are_still_required():
    x=value()
    for i in range(1,80):
        r=x.advance(ros_ns=i*20_000_000,wall_ns=i*20_000_000,
            center_z=.0199,forces=(30.,0.,30.,30.),capture_ns=i*20_000_000)
        assert not r.complete
    assert x.z==x.rest_z
    with pytest.raises(ValueError,match='original wall deadline'):
        x.advance(ros_ns=1_600_000_000,wall_ns=10_000_000_000,
            center_z=.0199,forces=(30.,30.,30.,30.),capture_ns=1_600_000_000)
