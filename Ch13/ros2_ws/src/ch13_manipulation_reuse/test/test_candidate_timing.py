"""Real two-roll OMPL paths: shortest raw time may be unexecutable."""
import json
from pathlib import Path
from types import SimpleNamespace
from rosidl_runtime_py.set_message import set_message_fields
from trajectory_msgs.msg import JointTrajectory
from ch13_manipulation_reuse.planning import Planner


def setup_planner():
    fixture=json.loads((Path(__file__).parent/'fixtures/pregrasp_time_candidates_v11.json').read_text())
    plans=[]
    for data in fixture['trajectories']:
        trajectory=JointTrajectory();set_message_fields(trajectory,data)
        plans.append({'trajectory':SimpleNamespace(joint_trajectory=trajectory)})
    planner=Planner.__new__(Planner);planner.records=[];planner.refine_execution_scale=False
    planner.joints=lambda:list(plans[0]['trajectory'].joint_trajectory.points[0].positions)
    planner.compute=lambda callback:callback()  # Scheduling only; real validator runs.
    return planner,plans


def test_choose_executable_normalized_route_instead_of_shortest_raw_route():
    planner,plans=setup_planner()
    original=[[p.time_from_start.sec+p.time_from_start.nanosec/1e9 for p in plan['trajectory'].joint_trajectory.points] for plan in plans]
    assert original[1][-1]<original[0][-1]
    # The shorter raw route needs scale2 for acceleration, so the scale1.25
    # longer raw route still wins. Both are now feasible; spacing rejects none.
    assert planner.choose_timed_plan(plans)==0
    for plan,times in zip(plans,original):
        assert [p.time_from_start.sec+p.time_from_start.nanosec/1e9 for p in plan['trajectory'].joint_trajectory.points]==times
    assert len([r for r in planner.records if r['kind']=='execution_candidate_timing'])==2
    assert planner.choose_timed_plan([plans[1]])==0


def test_all_time_inadmissible_candidates_are_rejected_without_execution():
    planner,plans=setup_planner()
    # A genuinely overlong route, rather than the previously over-gated short
    # final knot in the real fixture, must still be rejected.
    for point in plans[1]['trajectory'].joint_trajectory.points:
        point.time_from_start.sec*=100
        point.velocities=[v/100 for v in point.velocities]
        point.accelerations=[a/10000 for a in point.accelerations]
    assert planner.choose_timed_plan([plans[1]]) is None
