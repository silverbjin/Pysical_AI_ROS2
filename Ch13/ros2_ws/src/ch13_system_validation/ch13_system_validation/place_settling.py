"""Measured support settling, separate from an arm action's joint tolerance."""
import math


class PlacementSupportGate:
    def __init__(self):
        self.since=None
        self.last_clock=None

    def update(self,clock_ns,arm_velocities,stationary,support_N):
        valid=(type(clock_ns) is int and clock_ns>=0
               and len(arm_velocities)==6
               and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=.003 for v in arm_velocities)
               and stationary is True
               and type(support_N) in (int,float) and math.isfinite(support_N) and support_N>.01)
        if not valid:
            self.since=None
            return False
        if self.last_clock is not None and clock_ns<self.last_clock:self.since=None
        self.last_clock=clock_ns
        if self.since is None:self.since=clock_ns
        return clock_ns-self.since>=500_000_000
