"""A stopped simulation clock must not keep a target usable indefinitely."""
import math
import time

import pytest

from integrated_robot_vision.freshness import ClockGate, LatestSlot


def test_uninitialized_zero_future_and_stale_stamps_fail_closed():
    gate = ClockGate()
    assert not gate.valid(1., 0, 1., 10., 10.)
    epoch = gate.observe(1., 10.)
    assert gate.valid(1., epoch, 1.1, 10.1, 10.)
    for stamp, now in [(0, 1.), (math.nan, 1.), (1.031, 1.), (1., 1.301)]:
        assert not gate.valid(stamp, epoch, now, 10.1, 10.)


def test_clock_pause_backward_jump_and_wall_receipt_age_invalidate():
    gate = ClockGate()
    epoch = gate.observe(2., 10.)
    gate.observe(2., 10.301)
    assert not gate.valid(2., epoch, 2., 10.301, 10.)
    assert gate.observe(1., 10.4) == epoch + 1
    assert not gate.valid(1., epoch, 1., 10.4, 10.4)
    epoch = gate.observe(1.1, 10.5)
    assert not gate.valid(1.1, epoch, 1.1, 10.5, 10.1)


def test_late_completion_rechecks_clock_epoch_and_ros_age():
    gate = ClockGate()
    epoch = gate.observe(1., 10.)
    assert gate.valid(.85, epoch, 1., 10., 10.)
    gate.observe(1.16, 10.16)  # processing/TF wait consumes remaining lifetime
    assert not gate.valid(.85, epoch, 1.16, 10.16, 10.)
    gate.observe(.5, 10.2)
    assert not gate.valid(.5, epoch, .5, 10.2, 10.2)


def test_latest_slot_has_capacity_one_and_close_wakes_waiter():
    slot = LatestSlot()
    for i in range(100):
        slot.replace(i)
    assert slot.take(0) == 99
    assert slot.take(0) is None
    slot.close()
    start = time.monotonic()
    assert slot.take(10.) is None
    assert time.monotonic() - start < .1
    with pytest.raises(RuntimeError):
        slot.replace(100)
