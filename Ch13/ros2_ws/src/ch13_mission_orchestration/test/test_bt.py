import time
from concurrent.futures import Future
import py_trees
from ch13_mission_orchestration.tasks import TaskPort, GoalTracker
from ch13_mission_orchestration.tree import Mission


def test_steps_wait_for_actual_completion_and_never_restart():
    p=TaskPort(); m=Mission(p)
    m.tick(); assert p.snapshot()['requested']==['navigate']
    for _ in range(3): m.tick()
    assert p.snapshot()['requested']==['navigate']
    p.complete('navigate',{'session':'s'}); m.tick()
    assert p.snapshot()['requested']==['navigate','find']
    p.complete('find',{'capture_ns':10}); m.tick()
    assert p.snapshot()['requested']==['navigate','find','pick']
    p.complete('pick',{}); m.tick(); assert m.terminal is None
    p.complete('finish',{}); m.tick(); assert m.terminal=='SUCCESS'
    for _ in range(4): m.tick()
    assert p.snapshot()['requested']==['navigate','find','pick','finish']


def test_low_battery_preempts_and_latches_after_battery_returns():
    p=TaskPort(); m=Mission(p); m.tick(); m.battery=10; m.tick()
    assert p.snapshot()['cancel_reason']=='low_battery'
    assert m.root.children[1].status==py_trees.common.Status.INVALID
    m.battery=100; p.close(0); m.tick(); assert m.terminal=='ABORTED'
    for _ in range(3): m.tick()
    assert 'pick' not in p.snapshot()['requested']


def test_worker_failure_propagates_without_success_or_next_task():
    p=TaskPort(); m=Mission(p); m.tick(); p.fail('camera fault'); p.close(1); m.tick()
    assert m.terminal=='FAILURE'
    assert p.snapshot()['requested']==['navigate']


class Handle:
    accepted=True
    def __init__(self): self.result=Future(); self.cancel=Future(); self.calls=0
    def get_result_async(self): return self.result
    def cancel_goal_async(self): self.calls+=1; return self.cancel


def test_late_acceptance_is_canceled_and_ack_is_not_terminal():
    sent=Future(); tracker=GoalTracker(); tracker.add(sent); tracker.cancel()
    tracker.poll(); h=Handle(); sent.set_result(h); tracker.poll()
    assert h.calls==1 and not tracker.drained
    h.cancel.set_result(object()); tracker.poll(); assert not tracker.drained
    h.result.set_result(type('Result',(),{'status':5})()); tracker.poll()
    assert tracker.drained and tracker.terminals==[5]


def test_rejected_goal_and_send_exception_are_drained():
    tracker=GoalTracker(); a=Future(); b=Future(); tracker.add(a); tracker.add(b)
    a.set_result(type('Rejected',(),{'accepted':False})()); b.set_exception(RuntimeError('transport'))
    tracker.poll(); assert tracker.drained and tracker.errors


def test_cancel_ack_and_terminal_are_separately_audited():
    tracker=GoalTracker(); sent=Future(); h=Handle(); sent.set_result(h); tracker.add(sent)
    tracker.cancel(); tracker.poll()
    assert tracker.audit()['cancel_requests']==1 and tracker.audit()['cancel_acks']==[]
    h.cancel.set_result(type('Ack',(),{'goals_canceling':[1]})());tracker.poll()
    assert tracker.audit()['cancel_acks']==[True] and not tracker.drained
    h.result.set_result(type('Result',(),{'status':5})());tracker.poll()
    assert tracker.audit()['terminals']==[5] and tracker.drained


def test_snapshots_cannot_mutate_authority_and_unknown_steps_rejected():
    p=TaskPort(); p.submit('navigate'); s=p.snapshot(); s['requested'].append('pick')
    assert p.snapshot()['requested']==['navigate']
    try: p.submit('transport')
    except ValueError: pass
    else: assert False
