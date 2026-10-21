"""8.8: Simulation-only policy action interlock; NOT a robot safety controller."""
from dataclasses import dataclass
from math import isfinite


class SafetyReject(ValueError):
    """Reject an unsafe or unverified command before any IO layer."""


@dataclass(frozen=True)
class GuardContract:
    dof: int = 6
    action_limit: float = 1.0
    slew_per_second: float = 4.0
    initial_limit: float = 0.1
    sensor_max_age: float = 0.25
    command_max_age: float = 0.5


class SimulationActionGuard:
    """Validate normalized policy actions before a *simulator* adapter only.

    No ROS publisher, motor driver, physical E-stop or safety integrity is provided.
    Rejects commands rather than silently clipping them.
    """

    def __init__(self, contract=None):
        self.contract = contract or GuardContract()
        c = self.contract
        if c.dof < 1 or min(c.action_limit, c.slew_per_second,
                            c.initial_limit, c.sensor_max_age,
                            c.command_max_age) <= 0:
            raise ValueError("invalid guard limits")
        self.reset()

    def reset(self):
        self._previous = None
        self._previous_time = None

    def accept(self, action, *, now, sensor_time, command_time,
               authority, estop, simulation_only=True):
        c = self.contract
        if not simulation_only:
            raise SafetyReject("physical hardware commands are not supported")
        if not authority or estop:
            raise SafetyReject("missing control authority or E-stop active")
        if not all(isfinite(float(t)) for t in (now, sensor_time, command_time)):
            raise SafetyReject("nonfinite timestamp")
        sensor_age, command_age = now - sensor_time, now - command_time
        if not (0 <= sensor_age <= c.sensor_max_age):
            raise SafetyReject("sensor timestamp is stale or in the future")
        if not (0 <= command_age <= c.command_max_age):
            raise SafetyReject("command timestamp is stale or in the future")
        try:
            values = tuple(float(x) for x in action)
        except (TypeError, ValueError) as exc:
            raise SafetyReject("invalid action sequence") from exc
        if len(values) != c.dof or not all(isfinite(v) for v in values):
            raise SafetyReject("invalid joint count or nonfinite action")
        if any(abs(v) > c.action_limit for v in values):
            raise SafetyReject("normalized action limit exceeded")
        if self._previous is None:
            if any(abs(v) > c.initial_limit for v in values):
                raise SafetyReject("startup action limit exceeded")
        else:
            dt = now - self._previous_time
            if not (dt > 0 and isfinite(dt)):
                raise SafetyReject("non-monotonic control time")
            if any(abs(v - p) > c.slew_per_second * dt
                   for v, p in zip(values, self._previous)):
                raise SafetyReject("action slew limit exceeded")
        self._previous = values
        self._previous_time = now
        return values
