"""Validate simulation observations without ROS or command integration."""
from copy import deepcopy
import math


def adapt_observation(message):
    """Retain measured pose/twist, acquisition stamp and physical frames.

    Covariances are teaching defaults, not calibrated noise. This simulation
    ground truth input must never be presented as real leg odometry.
    """
    if (message.header.frame_id, message.child_frame_id) != ('odom', 'base_footprint'):
        raise ValueError('Expected odom -> base_footprint observation')
    stamp = message.header.stamp
    if stamp.sec < 0 or not 0 <= stamp.nanosec < 1_000_000_000:
        raise ValueError('Invalid acquisition timestamp')
    pose, twist = message.pose.pose, message.twist.twist
    values = [getattr(v, a) for v in (pose.position, twist.linear, twist.angular)
              for a in ('x', 'y', 'z')]
    q = [getattr(pose.orientation, a) for a in ('x', 'y', 'z', 'w')]
    if not all(math.isfinite(v) for v in values + q):
        raise ValueError('Nonfinite observation')
    if abs(sum(v * v for v in q) - 1.0) > 0.01:
        raise ValueError('Non-unit observation quaternion')
    result = deepcopy(message)
    result.pose.covariance = [0.0] * 36
    result.twist.covariance = [0.0] * 36
    for i, variance in zip(range(0, 36, 7), (0.0025, 0.0025, 0.0025, 0.01, 0.01, 0.01)):
        result.pose.covariance[i] = variance
    for i in range(0, 36, 7):
        result.twist.covariance[i] = 0.01
    return result


class ObservationStream:
    """Reject duplicate samples and require restart after simulation reset."""

    def __init__(self):
        self.last_stamp = None
        self.time_reversed = False

    def accept(self, message):
        if self.time_reversed:
            raise ValueError('Simulation time reversed: restart the full bringup.')
        observation = adapt_observation(message)
        stamp = message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec
        if self.last_stamp is not None and stamp < self.last_stamp:
            self.time_reversed = True
            raise ValueError('Simulation time reversed: restart the full bringup.')
        if stamp == self.last_stamp:
            return None
        self.last_stamp = stamp
        return observation
