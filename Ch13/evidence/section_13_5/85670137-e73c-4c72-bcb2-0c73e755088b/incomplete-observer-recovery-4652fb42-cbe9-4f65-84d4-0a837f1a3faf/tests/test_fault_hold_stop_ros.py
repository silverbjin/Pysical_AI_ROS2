"""Actual ROS status/lifecycle boundary; no native engine or G2 success claim."""
from lifecycle_msgs.msg import Transition
from test_crawl_lifecycle import crawl_rig


def test_fault_status_can_confirm_measured_hold_stop_but_never_ready_or_new_commands(crawl_rig,monkeypatch):
    rig=crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.1)
    reason='shift timeout; measured support/settle not gained'
    publications=[];publish=rig.guard.legs.publish
    def record(message):
        publications.append(message)
        publish(message)
    monkeypatch.setattr(rig.guard.legs,'publish',record)
    with rig.guard.lock:
        # Inject the observed failure at the owner boundary. The fixture is a
        # stationary feedback producer, not a simulated successful crawl.
        machine=rig.guard.machine
        machine.phase='SHIFT';machine._unload_start=None
        machine._fail(reason);machine.request_stop(urgent=True)
    rig.mode_name='STOP'
    rig.pump(.7)
    assert rig.crawl_states[-1].state=='FAULT'
    assert not rig.crawl_states[-1].stopped and not publications
    rig.pump(.7)
    state=rig.crawl_states[-1]
    assert state.stopped, 'measured fault stop never crossed the actual ROS status boundary'
    assert state.state=='FAULT' and state.fault_reason==reason and not state.ready
    assert not publications, 'read-only stop observation emitted a motor reference'
    assert rig.transition(Transition.TRANSITION_DEACTIVATE)
    rig.pump(.1)
    state=rig.crawl_states[-1]
    assert state.state=='INACTIVE' and state.fault_reason==reason
    assert not state.ready and not state.stopped and not publications
