import math
import numpy as np
import pytest
from ch13_manipulation_reuse.trajectory import Trajectory, JOINTS

LIMITS=[(-2.,2.)]*6

def points():
    return [dict(time=0.,positions=[0.]*6),dict(time=2.,positions=[.02]*6)]

def make(data=None,names=JOINTS):
    return Trajectory.from_points(names,points() if data is None else data,[0.]*6,LIMITS)

def test_quintic_actual_time_and_derivatives():
    path=make()
    q,v,a=path.sample(1.)
    np.testing.assert_allclose(q,[.01]*6,atol=1e-12)
    np.testing.assert_allclose(v,[.01875]*6,atol=1e-12)
    np.testing.assert_allclose(a,[0.]*6,atol=1e-12)
    np.testing.assert_allclose(path.sample(3.)[0],[.02]*6)
    np.testing.assert_allclose(path.sample(3.)[1],[0.]*6,atol=1e-12)

def test_permuted_wire_joints_are_normalized():
    data=points();data[1]['positions']=[.001,.002,.003,.004,.005,.006]
    q,_,_=make(data,names=tuple(reversed(JOINTS))).sample(2.)
    np.testing.assert_allclose(q,[.006,.005,.004,.003,.002,.001])

@pytest.mark.parametrize('names',[JOINTS[:-1],('joint1',)*6,JOINTS[:-1]+('joint8',)])
def test_wrong_joint_sets_rejected(names):
    with pytest.raises(ValueError):make(names=names)

@pytest.mark.parametrize('bad',[float('nan'),float('inf')])
def test_nonfinite_rejected(bad):
    data=points();data[1]['positions'][2]=bad
    with pytest.raises(ValueError):make(data)

@pytest.mark.parametrize('time',[0.,-.1,float('nan')])
def test_invalid_time_rejected(time):
    data=points();data[1]['time']=time
    with pytest.raises(ValueError):make(data)

def test_initial_position_jump_rejected():
    data=points();data[0]['positions'][0]=.1
    with pytest.raises(ValueError,match='start'):make(data)

def test_velocity_acceleration_and_joint_limits_include_interior_extrema():
    for positions,time in [([.2]*6,2.),([.02]*6,.2),([2.1]*6,100.)]:
        data=points();data[1].update(positions=positions,time=time)
        with pytest.raises(ValueError):make(data)
    data=points();data[1]['velocities']=[.01]*6
    with pytest.raises(ValueError,match='terminal'):make(data)

def test_cancel_is_continuous_and_brakes_to_hold_within_caps():
    path=make()
    before=path.sample(.7)
    brake=path.brake(.7)
    for actual,expected in zip(brake.sample(0.),before):
        np.testing.assert_allclose(actual,expected,atol=1e-10)
    q,v,a=brake.sample(brake.duration)
    np.testing.assert_allclose(v,[0.]*6,atol=1e-10)
    np.testing.assert_allclose(a,[0.]*6,atol=1e-10)
    for t in np.linspace(0,brake.duration,100):
        q,v,a=brake.sample(t)
        assert np.max(np.abs(v))<=.05+1e-10
        assert np.max(np.abs(a))<=.1+1e-10

def test_nonfinite_sample_time_is_not_a_valid_command():
    with pytest.raises(ValueError):make().sample(float('nan'))

def test_trajectory_cannot_mutate_after_admission():
    data=points();path=make(data);data[1]['positions'][0]=1.
    assert path.sample(2.)[0][0]==pytest.approx(.02)
