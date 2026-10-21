"""Bounded acquisition-time IMU history; unavailable orientation is not level."""
from collections import deque
import math


def unit(q):
    if len(q) != 4 or not all(math.isfinite(v) for v in q):
        raise ValueError('Invalid quaternion')
    norm = math.sqrt(sum(v*v for v in q))
    if abs(norm - 1) > .05:
        raise ValueError('Non-unit quaternion')
    return tuple(v/norm for v in q)


def multiply(a, b):
    ax, ay, az, aw = unit(a)
    bx, by, bz, bw = unit(b)
    return unit((aw*bx+ax*bw+ay*bz-az*by,
                 aw*by-ax*bz+ay*bw+az*bx,
                 aw*bz+ax*by-ay*bx+az*bw,
                 aw*bw-ax*bx-ay*by-az*bz))


class AttitudeHistory:
    def __init__(self, max_delta=.03, capacity=400):
        if not math.isfinite(max_delta) or max_delta <= 0 or capacity < 1:
            raise ValueError('Invalid history bounds')
        self.max_delta_ns = round(max_delta*1e9)
        self.samples = deque(maxlen=capacity)

    def add(self, stamp_ns, quaternion, available=True):
        if stamp_ns <= 0:
            return
        if self.samples and stamp_ns < self.samples[-1][0]:
            # Small out-of-order DDS delivery must not erase valid orientation
            # history. A substantial rewind marks a new simulation time epoch.
            if self.samples[-1][0] - stamp_ns <= self.max_delta_ns:
                return
            self.samples.clear()
        try:
            q = unit(quaternion) if available else None
        except ValueError:
            q = None
        self.samples.append((stamp_ns, q))

    def nearest(self, stamp_ns):
        if not self.samples:
            return None
        stamp, q = min(self.samples, key=lambda sample: abs(sample[0]-stamp_ns))
        return q if abs(stamp-stamp_ns) <= self.max_delta_ns else None
