import json
from pathlib import Path
import numpy as np
from ch13_manipulation_reuse.retime import normalize_points
from ch13_manipulation_reuse.trajectory import Trajectory


def test_actual_totg_boundary_derivatives_can_end_in_bounded_hold():
    root=Path(__file__).resolve().parents[5]
    data=json.loads((root/'Ch13/evidence/section_13_6_reuse/2ece9bb8-1960-44de-b92b-31325ae5dc18/run/moveit_probe.json').read_text())
    msg=data['records'][0]['trajectory']['joint_trajectory']
    points=[dict(time=p['time_from_start']['sec']+p['time_from_start']['nanosec']/1e9,
                 positions=p['positions'],velocities=p['velocities'],accelerations=p['accelerations']) for p in msg['points']]
    limits=[[-2.618,2.618],[0,3.14],[-2.697,0],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]]
    normalized,scale=normalize_points(msg['joint_names'],points,points[0]['positions'],limits)
    path=Trajectory.from_points(tuple(msg['joint_names']),normalized,points[0]['positions'],limits)
    assert scale>=1.
    assert path.duration>=points[-1]['time']
    np.testing.assert_allclose(path.sample(path.duration)[1],[0.]*6,atol=1e-8)
    np.testing.assert_allclose(path.sample(path.duration)[2],[0.]*6,atol=1e-8)
    for old,new in zip(points,normalized):np.testing.assert_array_equal(old['positions'],new['positions'])
