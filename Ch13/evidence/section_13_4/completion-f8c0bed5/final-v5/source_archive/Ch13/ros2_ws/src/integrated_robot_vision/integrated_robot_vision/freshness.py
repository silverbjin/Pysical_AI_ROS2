"""Capture-time and steady-time freshness, plus one-item bounded work queues."""
import math
from threading import Condition, RLock


class ClockGate:
    def __init__(self, max_age=.3, future_slop=.03):
        if not math.isfinite(max_age) or max_age <= 0 or not 0 <= future_slop < max_age:
            raise ValueError('invalid clock freshness limits')
        self.max_age, self.future_slop = max_age, future_slop
        self.epoch, self.last_ros, self.last_wall, self.advanced_wall = 0, None, None, None
        self.lock = RLock()

    def observe(self, ros_now: float, wall_now: float) -> int:
        if not math.isfinite(ros_now) or not math.isfinite(wall_now):
            raise ValueError('finite clocks required')
        with self.lock:
            if self.last_ros is not None and (ros_now < self.last_ros - 1e-9 or wall_now < self.last_wall):
                self.epoch += 1
                self.advanced_wall = None
            if ros_now > 0 and (self.last_ros is None or ros_now > self.last_ros or self.advanced_wall is None):
                self.advanced_wall = wall_now
            self.last_ros, self.last_wall = ros_now, wall_now
            return self.epoch

    def valid(self, stamp: float, epoch: int, ros_now: float,
              wall_now: float, receipt_wall: float) -> bool:
        with self.lock:
            if (self.last_ros is None or self.advanced_wall is None or epoch != self.epoch
                    or not all(math.isfinite(v) for v in (stamp, ros_now, wall_now, receipt_wall))):
                return False
            return (stamp > 0 and ros_now > 0 and ros_now >= self.last_ros - 1e-9
                    and -.0 <= wall_now - receipt_wall <= self.max_age
                    and 0 <= wall_now - self.advanced_wall <= self.max_age
                    and -self.future_slop <= ros_now - stamp <= self.max_age)


class LatestSlot:
    def __init__(self):
        self.condition, self.item, self.closed = Condition(), None, False

    def replace(self, item) -> None:
        with self.condition:
            if self.closed:
                raise RuntimeError('work queue is closed')
            self.item = item
            self.condition.notify()

    def take(self, timeout: float):
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError('finite nonnegative timeout required')
        with self.condition:
            self.condition.wait_for(lambda: self.item is not None or self.closed, timeout=timeout)
            item, self.item = self.item, None
            return item

    def close(self) -> None:
        with self.condition:
            self.closed, self.item = True, None
            self.condition.notify_all()
