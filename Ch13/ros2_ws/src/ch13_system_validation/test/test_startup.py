"""Cold middleware type imports belong before the live manipulation lease."""
from pathlib import Path
from ch13_system_validation.startup import prepare_manipulation_types


def test_prepare_covers_actual_actions_and_moveit_services_before_live_work(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4]/'scripts/reuse_13_6'))
    seen=[]
    records=prepare_manipulation_types(check=lambda kind:seen.append(kind.__name__))
    assert set(seen)=={'FollowJointTrajectory','GripperCommand','NavigateToPose',
        'GetMotionPlan','GetCartesianPath','ApplyPlanningScene','GetPlanningScene'}
    assert len(seen)==len(set(seen))
    assert all(row['end_wall']>=row['start_wall'] for row in records)
    assert all(row['scope']=='initialization_only_no_client_or_goal' for row in records)
