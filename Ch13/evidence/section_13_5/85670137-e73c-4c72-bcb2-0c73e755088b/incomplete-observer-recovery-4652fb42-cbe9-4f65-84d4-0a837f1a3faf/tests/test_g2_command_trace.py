"""A bounded command trace proves the test producer, not physical locomotion."""
from copy import deepcopy
import pytest
from integrated_robot_navigation import g2_command_source as api
from integrated_robot_navigation.carry_profile import default_limits


def trace():
    return [dict(event='publish',wall_ns=1000000000+i*20000000,raw=[.01,.03],
        smoothed=[i*.0004,i*.0012]) for i in range(3)]+[
        dict(event='stop_zero',wall_ns=1045000000,raw=[0.,0.],smoothed=[0.,0.])]


def test_full_command_trace_requires_bounded_normal_publications_and_a_final_zero():
    assert hasattr(api,'assess_command_trace'),'full G2 command trace assessment missing'
    assert api.assess_command_trace(trace(),default_limits())['passed'] is True


@pytest.mark.parametrize('bad',['speed','accel','period','missing_stop','after_stop','nan'])
def test_invalid_trace_cannot_be_presented_as_a_bounded_test_producer(bad):
    assert hasattr(api,'assess_command_trace'),'full G2 command trace assessment missing'
    rows=trace()
    if bad=='speed':rows[1]['raw'][0]=.1
    elif bad=='accel':rows[1]['smoothed'][0]=.001
    elif bad=='period':rows[1]['wall_ns']-=1
    elif bad=='missing_stop':rows.pop()
    elif bad=='after_stop':rows.append(deepcopy(rows[0]))
    else:rows[0]['raw'][0]=float('nan')
    assert api.assess_command_trace(rows,default_limits())['passed'] is False
