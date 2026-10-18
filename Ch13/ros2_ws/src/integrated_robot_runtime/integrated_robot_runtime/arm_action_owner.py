"""One asynchronous arm trajectory lease, including the unacknowledged-send window."""
from collections import deque
from dataclasses import dataclass
from threading import RLock
import uuid

from unique_identifier_msgs.msg import UUID


@dataclass
class PendingTrajectory:
    identifier: bytes
    deadline: float
    handle: object = None
    result: object = None
    terminal: bool = False
    cancel_at: float | None = None
    cancel_sent: bool = False
    error: str = ''


class ArmActionOwner:
    def __init__(self, client):
        self.client = client
        self.lock = RLock()
        self.pending = None
        self.known_ids = deque(maxlen=256)
        self.fault = ''

    def send(self, goal, *, now, timeout):
        with self.lock:
            if self.pending is not None or self.fault:
                raise RuntimeError('arm trajectory is reserved or fault latched')
            identifier = uuid.uuid4().bytes
            record = PendingTrajectory(identifier, now + timeout)
            self.pending = record
            self.known_ids.append(identifier)  # BEFORE transport can expose controller status
            try:
                future = self.client.send_goal_async(goal, goal_uuid=UUID(uuid=list(identifier)))
                future.add_done_callback(lambda value: self._accepted(record, value))
            except Exception as exc:
                self._unknown(record, exc)
            return record

    def _unknown(self, record, exc):
        record.error = self.fault = str(exc)
        # A transport exception is not proof the motor never received the goal.

    def _finish(self, record):
        record.terminal = True
        if self.pending is record:
            self.pending = None

    def _accepted(self, record, future):
        with self.lock:
            try:
                record.handle = future.result()
                if not record.handle.accepted:
                    record.error = 'trajectory rejected'
                    self._finish(record)
                    return
                record.handle.get_result_async().add_done_callback(
                    lambda value: self._result(record, value))
                if record.cancel_at is not None and not record.terminal:
                    self._cancel(record)
            except Exception as exc:
                self._unknown(record, exc)

    def _result(self, record, future):
        with self.lock:
            try:
                record.result = future.result()
                if record.result.status not in (4, 5, 6):
                    raise RuntimeError('nonterminal action result')
                self._finish(record)
            except Exception as exc:
                self._unknown(record, exc)

    def _cancel(self, record):
        if record.handle is not None and not record.cancel_sent:
            record.cancel_sent = True
            try:
                record.handle.cancel_goal_async().add_done_callback(
                    lambda value: self._cancel_ack(record, value))
            except Exception as exc:
                self._unknown(record, exc)

    def _cancel_ack(self, record, future):
        with self.lock:
            try:
                future.result()  # ACK alone does not imply terminal controller execution.
            except Exception as exc:
                self._unknown(record, exc)

    def cancel(self, *, now):
        with self.lock:
            record = self.pending
            if record is not None:
                if record.cancel_at is None:
                    record.cancel_at = now
                self._cancel(record)

    def watchdog(self, *, now):
        with self.lock:
            if self.pending is None:
                return
            if now >= self.pending.deadline:
                self.cancel(now=now)
            if self.pending.cancel_at is not None and now - self.pending.cancel_at >= .5:
                self.fault = 'terminal cancellation acknowledgement timeout'

    def recover(self):
        with self.lock:
            if self.pending is not None:
                return False
            self.fault = ''
            return True

    def is_foreign(self, identifier, status):
        with self.lock:
            return status in (1, 2, 3) and identifier not in self.known_ids
