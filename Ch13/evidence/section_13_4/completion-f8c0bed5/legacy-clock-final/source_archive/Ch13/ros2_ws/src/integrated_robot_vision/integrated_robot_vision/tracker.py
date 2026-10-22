"""One selected target, identity-local LPF, no lease extension on bad data."""
from dataclasses import replace
import math
import uuid

import numpy as np

from .contracts import TrackEstimate, vector
from .freshness import ClockGate


class TargetFilter:
    def __init__(self, tau=.2, alpha=None):
        if not math.isfinite(tau) or tau <= 0 or (
                alpha is not None and (not math.isfinite(alpha) or not 0 < alpha <= 1)):
            raise ValueError('positive finite tau and optional alpha in (0,1] required')
        self.tau, self.alpha, self.point, self.stamp = tau, alpha, None, None

    def update(self, point: np.ndarray, stamp: float) -> np.ndarray:
        point = vector(point, (3,))
        if not math.isfinite(stamp) or stamp <= 0 or (self.stamp is not None and stamp <= self.stamp):
            raise ValueError('strictly increasing positive capture stamps required')
        if self.point is None:
            self.point = point.copy()
        else:
            alpha = self.alpha if self.alpha is not None else 1-math.exp(-(stamp-self.stamp)/self.tau)
            self.point = alpha*point + (1-alpha)*self.point
        self.stamp = stamp
        return self.point.copy()


def iou(a, b):
    left, right = max(a.cx-a.width/2, b.cx-b.width/2), min(a.cx+a.width/2, b.cx+b.width/2)
    top, bottom = max(a.cy-a.height/2, b.cy-b.height/2), min(a.cy+a.height/2, b.cy+b.height/2)
    overlap = max(0., right-left)*max(0., bottom-top)
    return overlap / (a.width*a.height+b.width*b.height-overlap)


class TrackManager:
    def __init__(self, *, tau=.2, alpha=None, instance_id=None):
        TargetFilter(tau, alpha)  # validate even before the first acquisition
        self.tau, self.alpha = tau, alpha
        self.instance_id, self.counter, self.epoch = instance_id or str(uuid.uuid4()), 0, 0
        self.gate, self.clock_epoch = ClockGate(), 0
        self.context, self.observation, self.estimate, self.filter = None, None, None, None
        self.accepted_stamp, self.accepted_wall, self.accepted_clock_epoch = 0., None, 0
        self.score, self.ttl_reported = 0., False

    def invalidate(self, status):
        if status not in ('LOST', 'INVALID', 'TF_UNAVAILABLE', 'RESET'):
            raise ValueError('known invalid target status required')
        if self.estimate is not None:
            self.estimate = replace(self.estimate, valid=False, status=status)
        if status in ('LOST', 'TF_UNAVAILABLE', 'RESET'):
            self.observation, self.filter = None, None
        return self.estimate

    def reset(self, reason: str, epoch: int) -> None:
        self.invalidate(reason)
        self.context, self.observation, self.filter = None, None, None
        self.epoch, self.accepted_stamp, self.accepted_wall = epoch, 0., None

    def _clock(self, ros_now, wall_now):
        epoch = self.gate.observe(ros_now, wall_now)
        changed = epoch != self.clock_epoch
        if changed and self.observation is not None:
            self.reset('RESET', self.epoch+1)
        self.clock_epoch = epoch
        return changed

    def expire(self, ros_now: float, wall_now: float):
        changed = self._clock(ros_now, wall_now)
        if changed:
            return self.estimate
        if self.estimate is None or self.accepted_wall is None or self.ttl_reported:
            return None
        if not self.gate.valid(self.accepted_stamp, self.accepted_clock_epoch,
                               ros_now, wall_now, self.accepted_wall):
            self.ttl_reported = True
            return self.invalidate('LOST')
        return None

    @staticmethod
    def unique(candidates, scores):
        ranked = sorted(zip(scores, candidates), key=lambda row: row[0], reverse=True)
        if not ranked or (len(ranked) > 1 and ranked[0][0]-ranked[1][0] <= .05+1e-9):
            return None
        return ranked[0][1]

    def update(self, observations, ros_now: float, wall_now: float):
        self.expire(ros_now, wall_now)
        if not observations:
            return self.invalidate('LOST')
        first = observations[0]
        context = (first.epoch, first.frame_id, first.calibration_id)
        if first.frame_id != 'odom':
            self.reset('RESET', first.epoch)
            return self.estimate
        if any((v.epoch, v.frame_id, v.calibration_id) != context or
               abs(v.stamp-first.stamp) > 1e-9 for v in observations):
            return self.invalidate('INVALID')
        if self.context != context:
            self.reset('RESET', first.epoch)
            self.context = context
        if first.stamp <= self.accepted_stamp:
            return self.invalidate('INVALID')
        candidates = [v for v in observations if v.box.score >= .5 and
                      self.gate.valid(v.stamp, self.clock_epoch, ros_now, wall_now, wall_now)]
        if not candidates:
            return self.invalidate('INVALID')
        if self.observation is None:
            chosen = self.unique(candidates, [v.box.score for v in candidates])
        else:
            same_class = [v for v in candidates if v.box.class_id == self.observation.box.class_id]
            if not same_class:
                chosen = self.unique(candidates, [v.box.score for v in candidates])
                if chosen is not None:
                    self.observation, self.filter = None, None
            else:
                matches = [v for v in same_class if iou(v.box, self.observation.box) >= .1 and
                           np.linalg.norm(v.point-self.observation.point) <= .2+1e-12]
                chosen = self.unique(matches, [iou(v.box, self.observation.box) for v in matches])
        if chosen is None:
            return self.invalidate('INVALID')
        if self.filter is None:
            self.counter += 1
            self.filter = TargetFilter(self.tau, self.alpha)
            identity = f'{self.instance_id}:{self.epoch}:{self.counter}'
        else:
            identity = self.estimate.track_id
        filtered = self.filter.update(chosen.point, chosen.stamp)
        self.observation, self.score = chosen, chosen.box.score
        self.accepted_stamp, self.accepted_wall = chosen.stamp, wall_now
        self.accepted_clock_epoch, self.ttl_reported = self.clock_epoch, False
        self.estimate = TrackEstimate(identity, chosen.box.class_id, chosen.stamp,
                                      filtered, chosen.covariance, True, 'TRACKED')
        return self.estimate
