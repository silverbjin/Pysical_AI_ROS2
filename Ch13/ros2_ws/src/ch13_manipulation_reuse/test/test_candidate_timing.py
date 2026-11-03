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
    planner=Planner.__new__(Planner);planner.records=[]
    planner.joints=lambda:list(plans[0]['trajectory'].joint_trajectory.points[0].positions)
    planner.compute=lambda callback:callback()  # Scheduling only; real validator runs.
    return planner,plans


def test_choose_executable_normalized_route_instead_of_shortest_raw_route():
    planner,plans=setup_planner()
    original=[[p.time_from_start.sec+p.time_from_start.nanosec/1e9 for p in plan['trajectory'].joint_trajectory.points] for plan in plans]
    assert original[1][-1]<original[0][-1]
    assert planner.choose_timed_plan(plans)==0
    for plan,times in zip(plans,original):
        assert [p.time_from_start.sec+p.time_from_start.nanosec/1e9 for p in plan['trajectory'].joint_trajectory.points]==times
    assert any(r['kind']=='execution_candidate_rejected' and r['candidate']==1 for r in planner.records)


def test_all_time_inadmissible_candidates_are_rejected_without_execution():
    planner,plans=setup_planner()
    assert planner.choose_timed_plan([plans[1]]) is None
