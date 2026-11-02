"""Break: guard data can arrive before this subscriber's matching /clock."""
from copy import deepcopy
import time

from lifecycle_msgs.msg import Transition
from test_crawl_lifecycle import crawl_rig


def test_future_guard_waits_for_local_clock_without_retagging_or_renewing_receipt(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.08)
    node = rig.guard
    with node.lock:
        previous = deepcopy(node.gate)
        stamp = previous.header.stamp.sec*1_000_000_000+previous.header.stamp.nanosec
        future = deepcopy(previous)
        future.header.stamp.sec, future.header.stamp.nanosec = divmod(stamp+2_000_000, 1_000_000_000)
        future.state = 'STOP'
        node._gate(future)  # deterministic production callback/clock ordering
        assert node._gate_valid(stamp, time.monotonic_ns()) == (True, '')
        assert node.gate.state == 'STAND'
        assert node._gate_valid(stamp+2_000_000, time.monotonic_ns()) == (True, '')
        assert node.gate.state == 'STOP'
        assert node.gate.header.stamp == future.header.stamp
        receipt = node.gate_receipt
        node._gate(future)  # duplicate delivery cannot extend validity
        assert node._gate_valid(stamp+2_000_000, receipt+200_000_001) == (False, 'guard:wall_age')
        assert node.gate_receipt == receipt
