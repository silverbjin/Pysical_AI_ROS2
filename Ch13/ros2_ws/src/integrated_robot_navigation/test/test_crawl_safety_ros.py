"""Fresh feedback, mode generation, pause, and sole-leg ownership over DDS."""
from lifecycle_msgs.msg import Transition
from std_msgs.msg import Float64MultiArray
from integrated_robot_interfaces.msg import FootContacts
from threading import Event, Thread
from test_crawl_lifecycle import crawl_rig


def activate(rig):
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.1)


def test_clock_pause_cannot_keep_leg_targets_fresh(crawl_rig):
    rig = crawl_rig
    activate(rig)
    rig.pump(.28, clock=False)
    assert rig.crawl_states[-1].state == 'FAULT'
    assert not rig.crawl_states[-1].stopped
    count = len(rig.commands)
    rig.pump(.1, clock=False)
    assert len(rig.commands) == count
    rig.pump(.15, clock=True)  # transport resumption cannot recover active fault
    assert rig.crawl_states[-1].state == 'FAULT'
    assert len(rig.commands) == count


def test_duplicate_leg_producer_stops_this_owners_commands(crawl_rig):
    rig = crawl_rig
    activate(rig)
    extra = rig.node.create_publisher(Float64MultiArray, '/leg_position_controller/commands', 10)
    rig.pump(.12)
    assert rig.crawl_states[-1].state == 'FAULT'
    count = len(rig.commands)
    rig.node.destroy_publisher(extra)
    rig.pump(.15)
    assert len(rig.commands) == count


def test_foreign_guard_generation_is_not_adopted_while_active(crawl_rig):
    rig = crawl_rig
    activate(rig)
    rig.generation = 1
    rig.pump(.1)
    assert not rig.crawl_states[-1].ready
    assert rig.crawl_states[-1].generation == 0
    assert rig.crawl_states[-1].fault_reason


def test_deactivation_preserves_fault_diagnostic_and_never_claims_ready(crawl_rig):
    rig = crawl_rig
    activate(rig)
    rig.pump(.28, clock=False)
    reason = rig.crawl_states[-1].fault_reason
    assert reason
    assert rig.transition(Transition.TRANSITION_DEACTIVATE)
    rig.pump(.08, clock=False)
    assert rig.crawl_states[-1].state == 'INACTIVE'
    assert rig.crawl_states[-1].fault_reason == reason
    assert not rig.crawl_states[-1].ready and not rig.crawl_states[-1].stopped


def test_invalid_parallel_ingress_is_latched_without_mutating_model_or_publishing(crawl_rig, monkeypatch):
    """Concurrent receiver boundary, not an engine or DDS scheduling verdict."""
    rig = crawl_rig
    activate(rig)
    owner = rig.guard
    advance = owner.machine.advance
    received = Event()
    states, workers = [], []

    def during_advance(*args, **kwargs):
        result = advance(*args, **kwargs)
        if received.is_set():
            return result
        def invalid_ingress():
            owner._sensor('contacts', FootContacts(epoch=1))
            states.append(owner.machine.state)
            received.set()
        worker = Thread(target=invalid_ingress)
        workers.append(worker)
        worker.start()
        assert received.wait(.15), 'receiver must not wait for the model owner lock'
        assert states == ['STAND'], 'receiver must not directly mutate the state machine'
        return result  # valid calculation must not publish after the latched input fault

    monkeypatch.setattr(owner.machine, 'advance', during_advance)
    count = len(rig.commands)
    try:
        rig.pump(.04)
    finally:
        for worker in workers:
            worker.join(timeout=1.)
            assert not worker.is_alive()
    assert rig.crawl_states[-1].state == 'FAULT'
    assert 'engine epoch changed' in rig.crawl_states[-1].fault_reason
    assert len(rig.commands) == count
    monkeypatch.setattr(owner.machine, 'advance', advance)
    rig.pump(.1)
    assert rig.crawl_states[-1].state == 'FAULT' and len(rig.commands) == count
