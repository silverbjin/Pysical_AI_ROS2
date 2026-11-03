"""Continuous spline bounds, rather than knot spacing, govern 2ms sampling."""
import copy,json
from pathlib import Path
import numpy as np
import pytest
from scipy.interpolate import BPoly
from ch13_manipulation_reuse.retime import normalize_points
from ch13_manipulation_reuse.trajectory import Trajectory,JOINTS

LIMITS=[[-2.618,2.618],[0.,3.14],[-2.697,0.],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]]


def real_path():
    data=json.loads((Path(__file__).parent/'fixtures/pregrasp_time_candidates_v11.json').read_text())['trajectories'][1]
    points=[dict(time=p['time_from_start']['sec']+p['time_from_start']['nanosec']/1e9,
                 positions=p['positions'],velocities=p['velocities'],accelerations=p['accelerations']) for p in data['points']]
    return data['joint_names'],points


def test_real_subtick_endpoint_preserves_waypoints_and_uniform_timing():
    names,original=real_path();before=copy.deepcopy(original)
    result,scale=normalize_points(names,original,original[0]['positions'],LIMITS)
    path=Trajectory.from_points(tuple(names),result,original[0]['positions'],LIMITS)
    assert path.duration<=120 and len(result)==len(original)
    assert min(np.diff(path.times))<.002
    assert original==before
    for a,b in zip(original,result):
        np.testing.assert_array_equal(a['positions'],b['positions'])
        assert b['time']==pytest.approx(a['time']*scale)
    # An independent Hermite spline verifies the polynomial and its derivatives,
    # including the short final segment; it does not use the adapter's formulas.
    reference=BPoly.from_derivatives(path.times,[[p[k] for k in ('positions','velocities','accelerations')] for p in result])
    samples=np.concatenate([np.array(path.times),np.linspace(path.times[-2],path.duration,31),np.linspace(0.,path.duration,100)])
    for t in samples:
        for derivative,actual in enumerate(path.sample(float(t))):
            np.testing.assert_allclose(actual,reference(t,nu=derivative),atol=(1e-12,1e-10,2e-7)[derivative],rtol=1e-6)
    # Continuous velocity/acceleration bounds also bound changes between physics
    # samples even when one or more knots lie inside that sampling interval.
    ticks=np.arange(0.,path.duration,.002)
    q=reference(ticks);v=reference(ticks,nu=1)
    assert np.max(abs(np.diff(q,axis=0)))<=.05*.002+1e-10
    assert np.max(abs(np.diff(v,axis=0)))<=.10*.002+1e-9


def test_stationary_nanosecond_segment_is_valid_but_nonadvancing_time_is_not():
    data=[dict(time=0.,positions=[0.]*6),dict(time=1e-9,positions=[0.]*6)]
    path=Trajectory.from_points(JOINTS,data,[0.]*6,[[-1.,1.]]*6)
    np.testing.assert_array_equal(path.sample(.5e-9)[0],[0.]*6)
    data[-1]['time']=0.
    with pytest.raises(ValueError,match='increase'):Trajectory.from_points(JOINTS,data,[0.]*6,[[-1.,1.]]*6)


def test_short_segment_cannot_hide_excessive_motion_or_acceleration():
    names,points=real_path();points[-2]['velocities'][0]=.04
    with pytest.raises(ValueError):normalize_points(names,points,points[0]['positions'],LIMITS)
    bad=[dict(time=0.,positions=[0.]*6),dict(time=.001,positions=[.01]*6)]
    with pytest.raises(ValueError,match='bound'):Trajectory.from_points(JOINTS,bad,[0.]*6,[[-1.,1.]]*6)
