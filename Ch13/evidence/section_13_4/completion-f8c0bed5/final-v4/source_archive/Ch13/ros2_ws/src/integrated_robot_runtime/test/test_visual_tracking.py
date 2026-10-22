"""Real concurrency and late-ack state tests, independent of ROS publishers."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from integrated_robot_runtime.visual_tracking import VisualTrackingGuard


def ready_conditions():
    return {key: True for key in ('active', 'arm_safe', 'joints_fresh', 'target_valid',
                                  'target_fresh', 'model_ready', 'camera_ready', 'legs_standing',
                                  'arm_free', 'no_external_producer', 'action_ready', 'clock_valid')}


def test_default_off_and_single_outstanding_goal_under_real_concurrency():
    guard = VisualTrackingGuard()
    assert not guard.enabled and guard.arm_available
    assert not guard.reserve(0)
    token = guard.enable(ready_conditions())
    assert not guard.arm_available
    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(guard.reserve, [token, token])) == 1
    guard.complete(token)
    assert guard.enabled and not guard.arm_available  # whole session owns arm
    assert guard.reserve(token)


@pytest.mark.parametrize('condition', list(ready_conditions()))
def test_enable_refuses_any_missing_safety_gate(condition):
    guard = VisualTrackingGuard()
    conditions = ready_conditions()
    conditions[condition] = False
    with pytest.raises(ValueError):
        guard.enable(conditions)
    assert guard.arm_available and not guard.enabled


def test_late_result_after_disable_cannot_reenable_or_send_a_successor():
    guard = VisualTrackingGuard()
    token = guard.enable(ready_conditions())
    assert guard.reserve(token)
    guard.disable('target lost')
    assert not guard.arm_available  # until own result/cancel acknowledgement
    guard.complete(token)
    assert not guard.enabled and guard.arm_available
    assert not guard.reserve(token)


def test_cancel_timeout_retains_reservation_until_ack_and_explicit_recovery():
    guard = VisualTrackingGuard()
    token = guard.enable(ready_conditions())
    guard.reserve(token)
    guard.disable('disable')
    guard.latch_fault('cancel timeout')
    assert not guard.recover(acknowledged=False)
    guard.complete(token)
    assert not guard.arm_available
    with pytest.raises(ValueError):
        guard.enable(ready_conditions())
    assert guard.recover(acknowledged=True)
    assert guard.arm_available and not guard.enabled


def test_unknown_external_activity_stops_session_without_reviving_it():
    guard = VisualTrackingGuard()
    token = guard.enable(ready_conditions())
    guard.disable('external trajectory producer')
    assert not guard.enabled and not guard.reserve(token)
