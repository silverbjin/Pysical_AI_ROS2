"""Validated, immutable, SI-unit contracts shared by vision workers."""
from dataclasses import dataclass
import math

import numpy as np


STATUSES = frozenset(('TRACKED', 'LOST', 'INVALID', 'TF_UNAVAILABLE', 'RESET'))


def finite(*values):
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('nonfinite numeric input')


def identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty identifier required')


def vector(value, shape):
    result = np.array(value, dtype=float, copy=True)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f'finite array of shape {shape} required')
    result.flags.writeable = False
    return result


def covariance(value):
    result = vector(value, (3, 3))
    if not np.allclose(result, result.T, atol=1e-12) or np.linalg.eigvalsh(result).min() < -1e-12:
        raise ValueError('symmetric positive semidefinite covariance required')
    return result


@dataclass(frozen=True)
class Intrinsics:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    frame_id: str
    calibration_id: str

    def __post_init__(self):
        finite(self.fx, self.fy, self.cx, self.cy)
        if any(type(x) is not int or x <= 0 for x in (self.width, self.height)):
            raise ValueError('positive integer image dimensions required')
        if min(self.fx, self.fy) <= 0:
            raise ValueError('positive focal lengths required')
        identifier(self.frame_id)
        identifier(self.calibration_id)


@dataclass(frozen=True)
class Box2D:
    cx: float
    cy: float
    width: float
    height: float
    class_id: str
    score: float

    def __post_init__(self):
        finite(self.cx, self.cy, self.width, self.height, self.score)
        if min(self.width, self.height) <= 0 or not 0 <= self.score <= 1:
            raise ValueError('positive box size and score in [0,1] required')
        identifier(self.class_id)


@dataclass(frozen=True)
class Observation:
    stamp: float
    epoch: int
    calibration_id: str
    frame_id: str
    box: Box2D
    point: np.ndarray
    covariance: np.ndarray

    def __post_init__(self):
        finite(self.stamp)
        if self.stamp <= 0 or type(self.epoch) is not int or self.epoch < 0:
            raise ValueError('positive capture time and nonnegative epoch required')
        identifier(self.calibration_id)
        identifier(self.frame_id)
        if not isinstance(self.box, Box2D):
            raise ValueError('Box2D required')
        object.__setattr__(self, 'point', vector(self.point, (3,)))
        object.__setattr__(self, 'covariance', covariance(self.covariance))


@dataclass(frozen=True)
class TrackEstimate:
    track_id: str
    class_id: str
    stamp: float
    point: np.ndarray
    covariance: np.ndarray
    valid: bool
    status: str

    def __post_init__(self):
        finite(self.stamp)
        if self.stamp <= 0 or self.status not in STATUSES:
            raise ValueError('capture timestamp and known status required')
        if self.valid and (not self.track_id or not self.class_id or self.status != 'TRACKED'):
            raise ValueError('valid track needs identity and TRACKED status')
        object.__setattr__(self, 'point', vector(self.point, (3,)))
        object.__setattr__(self, 'covariance', covariance(self.covariance))
