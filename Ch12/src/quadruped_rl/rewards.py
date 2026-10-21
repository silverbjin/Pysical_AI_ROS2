"""Section 12.3 reward arithmetic, separated from physics for direct inspection."""
from dataclasses import dataclass, fields
import math
from numbers import Integral

import numpy as np


@dataclass(frozen=True)
class RewardConfig:
    linear_weight: float = 1.0
    yaw_weight: float = .5
    orientation_weight: float = .5
    torque_weight: float = .0001
    action_rate_weight: float = .01
    collision_weight: float = 1.0
    fall_penalty: float = 10.0
    linear_sigma: float = .25
    yaw_sigma: float = .25
    orientation_sigma: float = .1

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field.name} must be a finite number")
            if value < 0 or (field.name.endswith('sigma') and value == 0):
                raise ValueError(f"{field.name} must be nonnegative; sigma must be positive")


def _vector(value, size, name):
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must have shape ({size},) and be finite")
    return result


def compute_reward_terms(config, *, linear_velocity, angular_velocity, gravity,
                         command, torques, action, previous_action, collision_count,
                         terminated, dt):
    """Return weighted contributions and raw diagnostics. Rate terms use dt;
    the fall penalty is a single event. All velocities/commands use body axes.
    """
    if not isinstance(config, RewardConfig):
        raise TypeError("config must be RewardConfig")
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("dt must be finite and positive")
    # bool subclasses int but is not a meaningful contact count.
    if isinstance(collision_count, bool) or not isinstance(collision_count, Integral) or collision_count < 0:
        raise ValueError("collision_count must be a nonnegative integer")
    lin = _vector(linear_velocity, 3, 'linear_velocity')
    ang = _vector(angular_velocity, 3, 'angular_velocity')
    gravity = _vector(gravity, 3, 'gravity')
    command = _vector(command, 3, 'command')
    torques = _vector(torques, 12, 'torques')
    action = _vector(action, 12, 'action')
    previous_action = _vector(previous_action, 12, 'previous_action')
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        raw = {
            'linear_tracking': float(np.exp(-np.sum((command[:2]-lin[:2])**2)/config.linear_sigma)),
            'yaw_tracking': float(np.exp(-(command[2]-ang[2])**2/config.yaw_sigma)),
            'orientation': float(np.exp(-np.sum((gravity-[0, 0, -1])**2)/config.orientation_sigma)),
            'torque_squared': float(np.sum(torques**2)),
            'action_delta_squared': float(np.sum((action-previous_action)**2)),
            'collision_bodies': int(collision_count),
        }
        gate = 0.0 if terminated else 1.0
        terms = {
            'linear_tracking': gate*config.linear_weight*raw['linear_tracking']*dt,
            'yaw_tracking': gate*config.yaw_weight*raw['yaw_tracking']*dt,
            'orientation': gate*config.orientation_weight*raw['orientation']*dt,
            'torque': -config.torque_weight*raw['torque_squared']*dt,
            'action_rate': -config.action_rate_weight*raw['action_delta_squared']*dt,
            'collision': -config.collision_weight*collision_count*dt,
            'termination': -config.fall_penalty if terminated else 0.0,
        }
    if not all(math.isfinite(value) for value in terms.values()) or not math.isfinite(sum(terms.values())):
        raise FloatingPointError("Non-finite reward; check weights and physical state")
    return terms, raw
