"""Fresh feedback, mode generation, pause, and sole-leg ownership over DDS."""
from lifecycle_msgs.msg import Transition
from std_msgs.msg import Float64MultiArray
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
