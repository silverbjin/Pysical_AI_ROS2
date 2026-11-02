"""Fresh feedback, mode generation, pause, and sole-leg ownership over DDS."""
from lifecycle_msgs.msg import Transition
from std_msgs.msg import Float64MultiArray
from geometry_msgs.msg import Twist
from integrated_robot_interfaces.msg import FootContacts
from threading import Event, Thread
import json,os,time,uuid
from pathlib import Path
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
    publications=[];publish=owner.legs.publish
    # Deliberately leave one valid, pre-fault DDS publication undelivered.
    # Receipt count cannot identify when that message was originally sent.
    owner.legs.publish(Float64MultiArray(data=list(rig.commands[-1].data)))
    def monitored_publish(message):
        publications.append(dict(wall_ns=time.monotonic_ns(),ingress_seen=received.is_set()))
        publish(message)
    monkeypatch.setattr(owner.legs,'publish',monitored_publish)

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
        target=os.environ.get('CH13_NAV_EVIDENCE')
        if target:
            Path(target, 'ingress-publication-boundary-'+str(uuid.uuid4())+'.json').write_text(json.dumps(dict(
                pre_fault_receipt_count=count,post_fault_receipt_count=len(rig.commands),
                actual_publications=publications,ingress_seen=received.is_set(),states=states)))
    assert rig.crawl_states[-1].state == 'FAULT'
    assert 'engine epoch changed' in rig.crawl_states[-1].fault_reason
    assert not publications, 'the model owner published after the injected input fault'
    monkeypatch.setattr(owner.machine, 'advance', advance)
    rig.pump(.1)
    assert rig.crawl_states[-1].state == 'FAULT' and not publications


def test_parallel_final_command_error_is_latched_before_owner_publishes(crawl_rig, monkeypatch):
    rig=crawl_rig
    activate(rig)
    owner=rig.guard
    advance=owner.machine.advance
    seen=Event(); workers=[]; states=[]; publications=[]
    def during_advance(*args,**kwargs):
        result=advance(*args,**kwargs)
        if seen.is_set():return result
        def receive_invalid():
            msg=Twist();msg.linear.y=1.
            info=dict(source_timestamp=time.time_ns(),
                publication_sequence_number=owner.command_order.last_publication_sequence+1000)
            owner._command(msg,info)
            states.append(owner.machine.state)
            seen.set()
        worker=Thread(target=receive_invalid);workers.append(worker);worker.start()
        assert seen.wait(.15), 'final command ingress waited on the model owner'
        assert states==['STAND'], 'a receiver mutated the state machine'
        return result
    monkeypatch.setattr(owner.machine,'advance',during_advance)
    monkeypatch.setattr(owner.legs,'publish',publications.append)
    try:rig.pump(.06)
    finally:
        for worker in workers:
            worker.join(timeout=1.);assert not worker.is_alive()
    assert not publications
    assert owner.machine.state=='FAULT'
    assert owner.machine.reason=='nonplanar final command'
