"""Command-derived teaching odometry, explicitly separate from observations."""
from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class OdomState:
    x: float
    y: float
    yaw: float
    vx: float
    vy: float
    wz: float


class CommandOdometry:
    """Forward-Euler demo; scale/noise affect the estimate, not Gazebo friction."""

    def __init__(self, scale=0.9, noise_stddev=0.01, angular_noise_stddev=0.005,
                 timeout=0.3, max_dt=0.2, seed=42):
        values = (scale, noise_stddev, angular_noise_stddev, timeout, max_dt)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Parameters must be finite')
        if scale < 0 or noise_stddev < 0 or angular_noise_stddev < 0 or timeout <= 0 or max_dt <= 0:
            raise ValueError('Invalid scale, noise, or timing parameter')
        self.scale, self.noise_stddev = scale, noise_stddev
        self.angular_noise_stddev = angular_noise_stddev
        self.timeout, self.max_dt = timeout, max_dt
        self.rng = random.Random(seed)
        self.x = self.y = self.yaw = self.elapsed = 0.0
        self.last_stamp = self.command_stamp = None
        self.command = (0.0, 0.0, 0.0)

    def set_command(self, vx, vy, wz, stamp_ns):
        if not isinstance(stamp_ns, int) or stamp_ns < 0 or not all(
                math.isfinite(v) for v in (vx, vy, wz)):
            raise ValueError('Invalid command')
        if self.command_stamp is not None and stamp_ns < self.command_stamp:
            raise ValueError('Out-of-order command timestamp')
        self.command = (vx, vy, wz)
        self.command_stamp = stamp_ns

    def step(self, stamp_ns):
        if not isinstance(stamp_ns, int) or stamp_ns < 0:
            raise ValueError('Invalid clock')
        dt = 0.0 if self.last_stamp is None else (stamp_ns-self.last_stamp)/1e9
        if dt < 0.0 or dt > self.max_dt:
            self.x = self.y = self.yaw = self.elapsed = 0.0
            self.command_stamp = None
            self.command = (0.0, 0.0, 0.0)
            dt = 0.0
        self.last_stamp = stamp_ns
        active = (self.command_stamp is not None and
                  0 <= (stamp_ns-self.command_stamp)/1e9 < self.timeout)
        vx = vy = wz = 0.0
        if active and any(v != 0.0 for v in self.command):
            vx = self.command[0]*self.scale + self.rng.gauss(0, self.noise_stddev)
            vy = self.command[1]*self.scale + self.rng.gauss(0, self.noise_stddev)
            wz = self.command[2]*self.scale + self.rng.gauss(0, self.angular_noise_stddev)
        self.x += (vx*math.cos(self.yaw)-vy*math.sin(self.yaw))*dt
        self.y += (vx*math.sin(self.yaw)+vy*math.cos(self.yaw))*dt
        angle = self.yaw+wz*dt
        self.yaw = math.atan2(math.sin(angle), math.cos(angle))
        self.elapsed += dt
        return OdomState(self.x, self.y, self.yaw, vx, vy, wz)


def covariance3(values, assumed_variance):
    """Respect known/missing covariance; replace all-zero unknown covariance."""
    if len(values) != 9 or not math.isfinite(assumed_variance) or assumed_variance <= 0:
        raise ValueError('Invalid covariance parameters')
    result = list(values)
    if not all(math.isfinite(v) for v in result):
        raise ValueError('Nonfinite covariance')
    if result[0] == -1.0:
        return result
    if any(result[i] < 0 for i in (0, 4, 8)):
        raise ValueError('Negative measurement variance')
    if all(v == 0 for v in result):
        result = [0.0]*9
        for i in (0, 4, 8):
            result[i] = assumed_variance
    return result
