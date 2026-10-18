"""Conservative physical grasp classification; closing a joint is never success."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class GraspObservation:
    time: float
    left_contact: bool
    right_contact: bool
    lift: float
    drift: float

@dataclass(frozen=True)
class GraspThresholds:
    lift: float = .03
    drift: float = .025
    hold: float = .5
    max_sample_gap: float = .11

@dataclass(frozen=True)
class GraspResult:
    success: bool
    hold_duration: float
    max_lift: float
    message: str

def classify_grasp(sequence, thresholds=None):
    t = thresholds or GraspThresholds()
    start, previous, best, lift = None, None, 0., 0.
    for o in sequence:
        finite = all(math.isfinite(v) for v in (o.time,o.lift,o.drift))
        if finite: lift=max(lift,o.lift)
        continuous = previous is None or 0 < o.time-previous <= t.max_sample_gap
        good = finite and o.left_contact and o.right_contact and o.lift >= t.lift and 0 <= o.drift <= t.drift
        if good:
            if start is None or not continuous: start=o.time
            best=max(best,o.time-start)
        else: start=None
        previous=o.time
    return GraspResult(best >= t.hold,best,lift,'physical bilateral grasp' if best >= t.hold else 'contact/lift/drift/hold criteria not met')
