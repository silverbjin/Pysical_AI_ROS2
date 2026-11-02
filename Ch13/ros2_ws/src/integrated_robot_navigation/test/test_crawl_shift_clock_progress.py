"""Reproduce native 7c3373df SHIFT timing; ideal geometry is not physics proof."""
from copy import deepcopy
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from test_gait import machine
from test_calibration_clock_progress import sample_at


def shifting(model, command):
    plant=IdealFeedback(model); value=machine(model,plant)
    for _ in range(220):
        result=value.advance(plant.state,command,plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(value,result)
        if (value.phase=='SHIFT' and value._shift_plan is None
                and .25<(plant.ros-value._phase_start)/1e9/value._shift_duration<.6):
            return value,plant
    raise AssertionError('moving SHIFT not reached')


@pytest.mark.parametrize('command',[(.01,0.,0.),(-.01,0.,0.),(0.,0.,.03)])
def test_delayed_crawl_shift_consumes_at_most_one_nominal_curve_step(nav_robot_model,command):
    normal,plant=shifting(nav_robot_model,command); delayed=deepcopy(normal)
    ros,wall=normal._last_ros,normal._last_wall
    a=normal.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),command,
        ros+20_000_000,wall+20_000_000)
    # Actual publication 5343 -> 5344, preserved 7c3373df source manifest a694f432.
    r,w=ros+72_000_000,wall+52_029_145
    b=delayed.advance(sample_at(plant.state,r,w),command,r,w)
    assert a.state!='FAULT' and b.state!='FAULT'
    assert np.allclose(delayed.reference_body,normal.reference_body,atol=1e-12), \
        'late control tick jumped several nominal SHIFT reference steps'
    assert delayed._phase_start==normal._phase_start
    assert delayed._last_ros==r and delayed._last_wall==w,'safety clocks retagged'


def test_shift_progress_cap_does_not_extend_sensor_expiry_or_control_gap(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    ros,wall=value._last_ros,value._last_wall
    result=value.advance(plant.state,(.01,0.,0.),ros+200_000_001,wall+200_000_001)
    assert result.state=='FAULT' and result.reason=='control gap'


def test_original_shift_timeout_still_uses_actual_ros_elapsed(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    # Fresh original measurements with an elapsed phase deadline cannot become
    # permission to finish an arbitrarily slowed curve.
    value._phase_start=plant.ros-int((value._shift_duration+1.1)*1e9)
    value._unload_start=None; value._shift_settled_start=None
    ros,wall=plant.ros,plant.wall
    result=value.advance(sample_at(plant.state,ros,wall),(.01,0.,0.),ros,wall)
    assert result.state=='FAULT' and 'shift timeout' in result.reason
