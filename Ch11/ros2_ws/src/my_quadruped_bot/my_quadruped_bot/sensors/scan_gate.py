"""ROS-independent scan age, rate and sensor-plane tilt gate."""
import math


class ScanGate:
    """Accept scans only when their acquisition-time orientation is usable.

    Quaternion is lidar -> a gravity-aligned frame (odom here), XYZW order.
    This rejects whole scans; it does not level or deskew their ranges.
    """

    def __init__(self, max_tilt_degrees=5.0, min_interval=0.15,
                 max_age=0.5, future_tolerance=0.05):
        values = (max_tilt_degrees, min_interval, max_age, future_tolerance)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Scan gate parameters must be finite')
        if not 0 <= max_tilt_degrees <= 180 or min_interval < 0 or max_age <= 0 or future_tolerance < 0:
            raise ValueError('Invalid scan gate parameter range')
        self.max_tilt = math.radians(max_tilt_degrees)
        self.min_interval_ns = round(min_interval * 1e9)
        self.max_age_ns = round(max_age * 1e9)
        self.future_ns = round(future_tolerance * 1e9)
        self.last_now_ns = None
        self.last_accepted_ns = None

    def check(self, stamp_ns, now_ns, quaternion):
        """Return accepted, stamp, stale, future, orientation, tilt or interval."""
        if self.last_now_ns is not None and now_ns < self.last_now_ns:
            self.last_accepted_ns = None
        self.last_now_ns = now_ns
        if stamp_ns <= 0 or now_ns <= 0:
            return 'stamp'
        if now_ns - stamp_ns > self.max_age_ns:
            return 'stale'
        if stamp_ns - now_ns > self.future_ns:
            return 'future'
        if len(quaternion) != 4 or not all(math.isfinite(v) for v in quaternion):
            return 'orientation'
        norm = math.sqrt(sum(v*v for v in quaternion))
        if abs(norm - 1.0) > 0.05:
            return 'orientation'
        x, y, _, _ = (v / norm for v in quaternion)
        tilt = math.acos(max(-1.0, min(1.0, 1.0 - 2.0*(x*x + y*y))))
        if tilt > self.max_tilt:
            return 'tilt'
        if self.last_accepted_ns is not None and stamp_ns - self.last_accepted_ns < self.min_interval_ns:
            return 'interval'
        self.last_accepted_ns = stamp_ns
        return 'accepted'
