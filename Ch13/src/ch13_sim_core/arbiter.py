"""Single-writer, name-based command arbitration in simulation time."""
from dataclasses import dataclass
import math
import numpy as np
from .contract import ordered_values

@dataclass(frozen=True)
class GroupCommand:
    names: tuple[str, ...]
    positions: np.ndarray
    stamp: float
    publisher_id: str

@dataclass(frozen=True)
class ArbitrationResult:
    targets: np.ndarray
    status: str
    stale_groups: tuple[str, ...]

class CommandArbiter:
    def __init__(self, contract, timeout=.25, future_tolerance=.05):
        self.contract = contract
        self.timeout, self.future_tolerance = timeout, future_tolerance
        self._owners, self._stamps = {}, {}
        self._pending, self._applied_stamps = {}, {}
        self._targets = contract.nominal
        self._now = None
        self._clock_reversed = False

    def update(self, group, cmd):
        g = self.contract.groups[group]
        if set(cmd.names) != set(g.names): raise ValueError('wrong group')
        values = ordered_values(cmd.names,cmd.positions,g.names)
        if not cmd.publisher_id: raise ValueError('empty owner')
        if not math.isfinite(cmd.stamp) or cmd.stamp < 0: raise ValueError('invalid time')
        if self._now is None: raise ValueError('clock not initialized')
        if self._clock_reversed: raise ValueError('clock reversed; restart arbiter for new epoch')
        if self._now is not None and (cmd.stamp > self._now+self.future_tolerance or cmd.stamp < self._now-self.timeout):
            raise ValueError('future/stale command')
        if group in self._stamps and cmd.stamp < self._stamps[group]: raise ValueError('out of order')
        if group in self._owners and self._owners[group] != cmd.publisher_id: raise ValueError('owner conflict')
        # All checks precede mutation. Resolve returns copies, never internal buffers.
        self._pending[group] = (np.clip(values,g.lower,g.upper).copy(),cmd.stamp)
        self._owners[group], self._stamps[group] = cmd.publisher_id,cmd.stamp

    def resolve(self, now):
        if not math.isfinite(now) or now < 0: raise ValueError('invalid clock')
        previous=self._now
        if previous is not None and now < previous: self._clock_reversed = True
        # Receiving a valid command is not the same as applying it. Only a new
        # trusted simulation tick can promote a pending target to the safe hold.
        if previous is not None and now > previous and not self._clock_reversed:
            for group,(values,stamp) in list(self._pending.items()):
                if 0 <= now-stamp <= self.timeout:
                    indices=[self.contract.names.index(n) for n in self.contract.groups[group].names]
                    self._targets[indices]=values
                    self._applied_stamps[group]=stamp
                    del self._pending[group]
                elif now-stamp>self.timeout:del self._pending[group]
        self._now = now
        stale = tuple(g for g in self.contract.groups if g not in self._applied_stamps or now-self._applied_stamps[g] > self.timeout)
        status = 'clock_reversed' if self._clock_reversed else ('clock_paused' if previous==now else ('stale_hold' if stale else 'active'))
        return ArbitrationResult(self._targets.copy(),status,stale)

    def reset_owner(self, group):
        if group not in self.contract.groups: raise ValueError('unknown group')
        self._owners.pop(group,None)
        self._stamps.pop(group,None)
        self._applied_stamps.pop(group,None)
        self._pending.pop(group,None)
