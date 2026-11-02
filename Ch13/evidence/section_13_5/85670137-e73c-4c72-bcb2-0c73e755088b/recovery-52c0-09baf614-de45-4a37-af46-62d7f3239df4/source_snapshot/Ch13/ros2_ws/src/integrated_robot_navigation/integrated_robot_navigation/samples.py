"""ROS capture time and local receipt time are independent safety clocks."""
from dataclasses import dataclass, fields, is_dataclass
import math
from collections.abc import Mapping

Vec3 = tuple[float, float, float]
JointMap = dict[str, float]


@dataclass(frozen=True)
class Sample:
    stamp_ns: int
    received_ns: int
    epoch: int
    sequence: int
    frame_id: str
    data: object


@dataclass(frozen=True)
class SensorBundle:
    joints: Sample | None
    imu: Sample | None
    contacts: Sample | None
    body: Sample | None
    scan: Sample | None
    carry: Sample | None


@dataclass(frozen=True)
class ControlResult:
    state: str
    phase: str
    swing_foot: str | None
    generation: int
    joint_targets: JointMap | None
    reason: str


@dataclass(frozen=True)
class ApproachCandidate:
    x: float
    y: float
    yaw: float
    standoff: float
    clearance: float
    arm_solution: JointMap


def _finite(value):
    if isinstance(value, (bool, str)):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(isinstance(k, str) and _finite(v) for k, v in value.items())
    if isinstance(value, (tuple, list)):
        return all(_finite(v) for v in value)
    if is_dataclass(value):
        return all(_finite(getattr(value, f.name)) for f in fields(value))
    return False


def sample_valid(sample: Sample | None, ros_ns: int, wall_ns: int, epoch: int,
                 *, max_age_ns: int) -> tuple[bool, str]:
    if sample is None:
        return False, 'missing'
    counters = (sample.stamp_ns, sample.received_ns, sample.epoch, sample.sequence,
                ros_ns, wall_ns, epoch, max_age_ns)
    if any(type(v) is not int or v < 0 for v in counters):
        return False, 'metadata'
    if sample.epoch != epoch:
        return False, 'epoch'
    if not 0 <= ros_ns - sample.stamp_ns <= max_age_ns:
        return False, 'ros_age'
    if not 0 <= wall_ns - sample.received_ns <= max_age_ns:
        return False, 'wall_age'
    if not sample.frame_id:
        return False, 'frame'
    if not _finite(sample.data):
        return False, 'nonfinite'
    return True, ''


def validate_bundle(bundle: SensorBundle, ros_ns: int, wall_ns: int,
                    epoch: int) -> tuple[bool, str]:
    for name in ('joints', 'imu', 'contacts', 'body', 'scan', 'carry'):
        age = 300_000_000 if name == 'scan' else 200_000_000
        ok, reason = sample_valid(getattr(bundle, name), ros_ns, wall_ns, epoch,
                                  max_age_ns=age)
        if not ok:
            return False, name + ':' + reason
    return True, ''


class ReceiptCache:
    """A capture cannot become fresh again by arriving twice.

    One instance belongs to a serialized receiver, not to concurrent workers.
    A caller must identify the engine epoch, never infer it from a late packet.
    """
    def __init__(self, epoch: int):
        if type(epoch) is not int or epoch < 0:
            raise ValueError('invalid epoch')
        self.epoch = epoch
        self._samples = {}

    def receive(self, stream: str, sample: Sample) -> Sample:
        if sample.epoch != self.epoch:
            raise ValueError('sample epoch mismatch')
        old = self._samples.get(stream)
        if old is not None:
            if (sample.stamp_ns, sample.sequence) == (old.stamp_ns, old.sequence):
                return old
            if (sample.stamp_ns <= old.stamp_ns or sample.sequence <= old.sequence
                    or sample.received_ns < old.received_ns):
                raise ValueError('sample order regression')
        self._samples[stream] = sample
        return sample

    def get(self, stream: str) -> Sample | None:
        return self._samples.get(stream)

    def reset(self, epoch: int) -> None:
        if type(epoch) is not int or epoch <= self.epoch:
            raise ValueError('epoch must increase')
        self.epoch = epoch
        self._samples.clear()
