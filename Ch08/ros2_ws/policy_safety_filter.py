"""Ch08 §8.8: numerical-only 6DOF normalized policy action guard.

No ROS 2 publisher, no motor command, no physical E-stop. This is a teaching
contract that MUST NOT be interpreted as certified robot safety software.
"""
from dataclasses import dataclass
import math
import numpy as np


class PolicyActionBlocked(ValueError):
    pass


@dataclass(frozen=True)
class FilterResult:
    raw: np.ndarray
    clipped: np.ndarray
    filtered: np.ndarray
    normalized_only: bool = True


class PolicyActionGuard:
    def __init__(self, dof=6, alpha=0.2, max_age_sec=0.25):
        if type(dof) is not int or dof < 1:
            raise ValueError("positive integer dof required")
        if not (math.isfinite(alpha) and 0.0 < alpha <= 1.0):
            raise ValueError("alpha must be 0 < alpha <= 1")
        if not (math.isfinite(max_age_sec) and max_age_sec > 0.0):
            raise ValueError("max_age_sec must be finite and positive")
        self.dof=dof
        self.alpha=float(alpha)
        self.max_age_sec=float(max_age_sec)
        self.previous=np.zeros(dof,dtype=np.float64)
        self.estop_latched=False

    def reset(self, operator_cleared_estop=False):
        if self.estop_latched and not operator_cleared_estop:
            raise PolicyActionBlocked("CH08_88_LATCHED_ESTOP_REQUIRES_EXPLICIT_CLEAR")
        self.previous[:]=0.0
        self.estop_latched=False

    def apply(self, action, message_age_sec, estop=False):
        if estop:
            self.estop_latched=True
            self.previous[:]=0.0
            raise PolicyActionBlocked("CH08_88_SOFTWARE_ESTOP_LATCHED")
        if self.estop_latched:
            raise PolicyActionBlocked("CH08_88_ESTOP_STILL_LATCHED")
        try:
            values=np.asarray(action,dtype=np.float64)
        except (TypeError,ValueError,OverflowError) as exc:
            raise PolicyActionBlocked("CH08_88_ACTION_NOT_NUMERIC") from exc
        if values.shape!=(self.dof,):
            raise PolicyActionBlocked("CH08_88_MODEL_DIMENSION_MISMATCH")
        if not np.isfinite(values).all():
            raise PolicyActionBlocked("CH08_88_NAN_INF_ACTION_REJECTED")
        try:
            age=float(message_age_sec)
        except (TypeError,ValueError,OverflowError) as exc:
            raise PolicyActionBlocked("CH08_88_BAD_STAMP") from exc
        if not math.isfinite(age) or age < 0 or age > self.max_age_sec:
            raise PolicyActionBlocked("CH08_88_STALE_OR_FUTURE_OBSERVATION")
        clipped=np.clip(values,-1.0,1.0)
        filtered=self.alpha*clipped+(1.0-self.alpha)*self.previous
        if not np.isfinite(filtered).all():
            raise PolicyActionBlocked("CH08_88_NUMERICAL_FAILURE")
        self.previous=filtered.copy()
        return FilterResult(
            raw=values.copy(), clipped=clipped.copy(),
            filtered=filtered.copy(),
        )
