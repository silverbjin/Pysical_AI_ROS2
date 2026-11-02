"""Bounded/coalesced notification is not command permission or an ACK."""
import importlib
import pytest


def gate():
    assert importlib.util.find_spec('integrated_robot_navigation.reference_dispatch'), \
        'single-owner reference wake admission missing'
    return importlib.import_module('integrated_robot_navigation.reference_dispatch').ReferenceDispatch()


@pytest.mark.parametrize('ros,wall',[(100_000_000,120_000_000),(120_000_000,119_999_999)])
def test_wall_period_and_original_clock_progress_are_both_required(ros,wall):
    value=gate();value.issued(100_000_000,100_000_000);value.defer()
    assert not value.allowed(ros,wall)
    assert not value.notify(ros,wall)
    assert not value.take_notification()
    assert value.allowed(120_000_000,120_000_000)
    assert value.notify(120_000_000,120_000_000)
    assert not value.notify(121_000_000,121_000_000), 'duplicate notification accumulated'
    assert value.take_notification() and not value.take_notification()


def test_new_issue_cancels_old_wait_and_never_releases_a_second_command_early():
    value=gate();value.issued(100_000_000,100_000_000);value.defer()
    assert value.notify(125_000_000,125_000_000)
    value.begin_tick()  # a regular timer can supersede a queued notification
    assert not value.take_notification()
    value.issued(125_000_000,125_000_000);value.defer()
    assert not value.notify(140_000_000,139_999_999)
    assert value.notify(140_000_000,140_000_000)
    value.cancel()
    assert not value.take_notification() and not value.notify(200_000_000,200_000_000)


def test_positive_original_ros_progress_is_not_a_second_wall_rate_limiter():
    value=gate();value.issued(100_000_000,100_000_000);value.defer()
    # The original clock is quantized/coalesced; no future data is used.
    # Wall control rate is 50Hz, and the trajectory consumes only these 18ms.
    assert value.allowed(118_000_000,120_000_000), 'coarse ROS samples inserted an extra control wait'
    assert value.notify(118_000_000,120_000_000)


def test_late_owner_wake_cannot_rebase_every_future_50hz_deadline():
    value=gate();value.issued(100_000_000,100_000_000)
    # A single late wake is actual jitter, not a new control-time origin.
    value.issued(125_000_000,125_000_000)
    assert value.allowed(140_000_000,140_000_000), '5ms wake delay was permanently added to every following period'
    value.issued(140_000_000,140_000_000)
    assert not value.allowed(159_999_999,159_999_999), 'two decisions consumed the same nominal slot'
    # Skip missed slots. Never execute a burst of banked controller steps.
    value.issued(185_000_000,185_000_000)
    assert not value.allowed(199_999_999,199_999_999)
    assert value.allowed(200_000_000,200_000_000)
