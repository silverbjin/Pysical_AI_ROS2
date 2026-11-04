from concurrent.futures import Future
import threading
from ch13_mission_orchestration.tasks import TaskPort,GoalTracker,DeferredClients,stop_worker


def test_clients_remain_alive_until_late_goal_is_canceled_and_terminal():
    tracker=GoalTracker();sent=Future();tracker.add(sent);destroyed=[];clients=DeferredClients(tracker)
    clients.defer(lambda:destroyed.append(True))
    result=Future();cancel=Future()
    class Handle:
        accepted=True
        def get_result_async(self):return result
        def cancel_goal_async(self):return cancel
    def until(predicate,timeout):
        assert not destroyed
        sent.set_result(Handle());tracker.poll()
        assert not destroyed and not predicate()
        cancel.set_result(type('Ack',(),{'goals_canceling':[1]})());tracker.poll()
        assert not predicate()
        result.set_result(type('Result',(),{'status':5})());tracker.poll()
        return predicate()
    clients.close(until)
    assert destroyed==[True] and tracker.terminals==[5]


def test_failed_drain_does_not_destroy_unresolved_action_client():
    tracker=GoalTracker();tracker.add(Future());destroyed=[];clients=DeferredClients(tracker)
    clients.defer(lambda:destroyed.append(True))
    try:clients.close(lambda predicate,timeout:False)
    except RuntimeError:pass
    else:assert False
    assert not destroyed


def test_exception_cleanup_cancels_and_joins_worker_before_context_shutdown():
    port=TaskPort();finished=threading.Event()
    def worker():
        while not port.snapshot()['cancel_reason']:finished.wait(.001)
        finished.set()
    thread=threading.Thread(target=worker);thread.start()
    assert stop_worker(thread,port,timeout=1.)
    assert finished.is_set() and not thread.is_alive()
