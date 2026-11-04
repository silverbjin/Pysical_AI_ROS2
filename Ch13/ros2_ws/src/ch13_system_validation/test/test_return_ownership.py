from concurrent.futures import Future
from types import SimpleNamespace
from ch13_mission_orchestration.tasks import GoalTracker
from ch13_system_validation.continuation import drain_owned_goals


def test_return_late_acceptance_and_result_before_cancel_ack_are_both_drained():
    tracker=GoalTracker();sent=Future();ack=Future();result=Future()
    class Handle:
        accepted=True
        def get_result_async(self):return result
        def cancel_goal_async(self):return ack
    tracker.add(sent);session=SimpleNamespace(goals=tracker);ticks=[]
    def until(predicate,timeout):
        for i in range(6):
            ticks.append(i)
            if i==1:sent.set_result(Handle())
            if i==2:result.set_result(SimpleNamespace(status=5))
            if i==4:ack.set_result(SimpleNamespace(goals_canceling=[1]))
            tracker.poll()
            if predicate():return True
        return False
    drain_owned_goals(session,until)
    assert ticks==[0,1,2,3,4]
    assert tracker.audit()['pending']==0
    assert tracker.audit()['terminals']==[5]
    assert tracker.audit()['cancel_acks']==[True]
