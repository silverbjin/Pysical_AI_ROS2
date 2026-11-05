import json
from pathlib import Path
import numpy as np
import pytest
from ch13_manipulation_reuse.retime import normalize_points
from ch13_manipulation_reuse.trajectory import Trajectory

LIMITS=[[-2.618,2.618],[0.,3.14],[-2.697,0.],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]]


def actual_plan():
    data=json.loads((Path(__file__).parent/'data/v19_pregrasp_totg.json').read_text())['trajectory']
    points=[dict(time=p['time_from_start']['sec']+p['time_from_start']['nanosec']/1e9,
                 positions=p['positions'],velocities=p['velocities'],accelerations=p['accelerations']) for p in data['points']]
    return tuple(data['joint_names']),points


def test_refinement_preserves_actual_full_path_and_continuous_bounds():
    names,points=actual_plan();current=points[0]['positions']
    coarse,old=normalize_points(names,points,current,LIMITS)
    refined,new=normalize_points(names,points,current,LIMITS,refine_scale=True)
    assert old==1.25 and 1.04<new<1.1
    before=Trajectory.from_points(names,coarse,current,LIMITS)
    after=Trajectory.from_points(names,refined,current,LIMITS)
    assert before.duration>93. and after.duration<81.
    assert len(coarse)==len(refined)==len(points)==751
    for source,result in zip(points,refined):np.testing.assert_array_equal(source['positions'],result['positions'])
    ratio=old/new
    for fraction in np.linspace(0,1,31):
        q,v,a=before.sample(before.duration*fraction);qq,vv,aa=after.sample(after.duration*fraction)
        np.testing.assert_allclose(qq,q,atol=1e-7)
        np.testing.assert_allclose(vv,v*ratio,atol=1e-7)
        np.testing.assert_allclose(aa,a*ratio**2,atol=1e-7)
    np.testing.assert_allclose(after.sample(after.duration)[1:],[np.zeros(6),np.zeros(6)],atol=1e-8)


def test_refinement_cannot_repair_or_hide_invalid_joint_positions():
    names,points=actual_plan();points[5]['positions'][0]=10.
    with pytest.raises(ValueError):normalize_points(names,points,points[0]['positions'],LIMITS,refine_scale=True)
