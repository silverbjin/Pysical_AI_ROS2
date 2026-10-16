"""Textbook small-angle complementary filter; no ROS or SciPy dependency."""
import math


def wrap_angle(angle):
    """Keep an angle in [-pi, pi]; this does not remove yaw drift."""
    return math.atan2(math.sin(angle), math.cos(angle))


class ComplementaryFilter:
    """Estimate roll/pitch from gravity and body rates near level attitude.

    Independent gx/gy/gz integration is the book's small-angle approximation,
    not a general SO(3) attitude estimator for large coupled rotations.
    """

    def __init__(self, alpha=0.98, max_dt=0.2):
        if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
            raise ValueError('alpha must be finite and between 0 and 1')
        if not math.isfinite(max_dt) or max_dt <= 0.0:
            raise ValueError('max_dt must be finite and positive')
        self.alpha = alpha
        self.max_dt = max_dt
        self.last_stamp_ns = None
        self.roll = self.pitch = self.yaw = 0.0

    def update(self, stamp_ns, acceleration, angular_velocity):
        """Use acquisition time, return radians, or None for a duplicate stamp.

        First sample, backwards time, and a gap > max_dt start a fresh estimate:
        roll/pitch from acceleration, yaw=0. Missing motion cannot be recovered.
        Invalid samples raise ValueError without advancing the filter clock.
        """
        if not isinstance(stamp_ns, int) or stamp_ns < 0:
            raise ValueError('stamp_ns must be a nonnegative integer')
        if len(acceleration) != 3 or len(angular_velocity) != 3:
            raise ValueError('Expected three acceleration and three gyro axes')
        ax, ay, az = acceleration
        gx, gy, gz = angular_velocity
        if not all(math.isfinite(v) for v in (ax, ay, az, gx, gy, gz)):
            raise ValueError('Nonfinite IMU sample')
        if math.hypot(ax, ay, az) < 1e-6:
            raise ValueError('Gravity direction unavailable: near-zero acceleration')
        roll_acc = math.atan2(ay, az)
        pitch_acc = math.atan2(-ax, math.hypot(ay, az))
        if self.last_stamp_ns == stamp_ns:
            return None
        dt = (None if self.last_stamp_ns is None
              else (stamp_ns-self.last_stamp_ns)/1e9)
        if dt is None or dt < 0.0 or dt > self.max_dt:
            self.roll, self.pitch, self.yaw = roll_acc, pitch_acc, 0.0
        else:
            roll_pred = self.roll + gx*dt
            pitch_pred = self.pitch + gy*dt
            # Equivalent to alpha*prediction+(1-alpha)*accel for small angles.
            # Shortest angular innovation avoids discontinuity at +/-pi.
            self.roll = wrap_angle(roll_pred + (1-self.alpha)*wrap_angle(roll_acc-roll_pred))
            self.pitch = wrap_angle(pitch_pred + (1-self.alpha)*wrap_angle(pitch_acc-pitch_pred))
            self.yaw = wrap_angle(self.yaw + gz*dt)
        self.last_stamp_ns = stamp_ns
        return self.roll, self.pitch, self.yaw
