"""Transport-boundary futures exercise the real ownership/cancel state machine."""
from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from integrated_robot_runtime.arm_action_owner import ArmActionOwner


class Transport:
    def __init__(self):
        self.acceptance = Future()
        self.result = Future()
        self.cancel = Future()
        self.cancels = 0

    def send_goal_async(self, goal, *, goal_uuid):
        self.uuid = bytes(goal_uuid.uuid)
        return self.acceptance

    def accept(self):
        self.acceptance.set_result(SimpleNamespace(
            accepted=True, get_result_async=lambda: self.result,
            cancel_goal_async=self.cancel_goal))

    def cancel_goal(self):
        self.cancels += 1
        return self.cancel


def test_pending_acceptance_is_reserved_and_late_acceptance_is_canceled():
    transport = Transport()
    owner = ArmActionOwner(transport)
    record = owner.send(object(), now=0., timeout=2.)
    assert owner.pending is record and transport.uuid in owner.known_ids
    assert owner.snapshot()['pending_uuid'] == transport.uuid.hex()
    assert owner.snapshot()['events'][-1]['event'] == 'sent'
    with pytest.raises(RuntimeError):
        owner.send(object(), now=.1, timeout=2.)
    owner.cancel(now=.1)
    transport.accept()
    assert transport.cancels == 1 and owner.pending is record
    assert owner.snapshot()['result_future_done'] is False
    transport.cancel.set_result(SimpleNamespace(goals_canceling=[object()]))
    assert owner.pending is record  # cancel response is not terminal execution result
    transport.result.set_result(SimpleNamespace(status=5))
    assert owner.pending is None and record.terminal and record.result.status == 5
    assert owner.snapshot()['events'][-1]['event'] == 'terminal'
    assert owner.snapshot()['events'][-1]['uuid'] == transport.uuid.hex()


def test_cancel_timeout_latches_fault_even_after_late_terminal_ack():
    transport = Transport()
    owner = ArmActionOwner(transport)
    owner.send(object(), now=0., timeout=2.)
    transport.accept()
    owner.cancel(now=.1)
    owner.watchdog(now=.7)
    assert owner.fault and owner.pending is not None
    assert not owner.recover()
    transport.result.set_result(SimpleNamespace(status=5))
    assert owner.fault and owner.pending is None
    with pytest.raises(RuntimeError):
        owner.send(object(), now=.8, timeout=2.)
    assert owner.recover()


def test_rejection_and_send_exception_do_not_leave_a_false_active_goal():
    transport = Transport()
    owner = ArmActionOwner(transport)
    record = owner.send(object(), now=0., timeout=2.)
    transport.acceptance.set_result(SimpleNamespace(accepted=False))
    assert record.terminal and owner.pending is None
    transport.acceptance = Future()
    record = owner.send(object(), now=1., timeout=2.)
    transport.acceptance.set_exception(RuntimeError('transport state unknown'))
    assert owner.fault and owner.pending is record  # fail closed, not a rejection


def test_only_unknown_live_statuses_are_foreign():
    transport = Transport()
    owner = ArmActionOwner(transport)
    owner.send(object(), now=0., timeout=2.)
    assert not owner.is_foreign(transport.uuid, 2)
    assert owner.is_foreign(bytes(16), 2)
    assert not owner.is_foreign(bytes(16), 4)
