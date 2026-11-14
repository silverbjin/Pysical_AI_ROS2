"""Ch07 #173 G01: fail-closed, one-shot target validation (no ROS imports).

Input is the real §7.5 /camera/target_3d_base PointStamped in base_link,
metres, stamped at image acquisition time. It is a *surface point*, not
automatically an object centre or TCP pose. No action is sent by this module.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Target:
    x: float
    y: float
    z: float
    stamp_s: float


class TargetGate:
    """Two fresh, spatially consistent frames; one accept per process lifetime.

    The existing upstream /camera/target_valid is a headerless Bool. It cannot
    prove synchronized object identity. Validity must be recent *and* the
    upstream §7.5 stamp/depth/TF checker remains authoritative. This prevents
    accidental stale replay; complete camera registration requires G02.
    """
    def __init__(self, *, max_age_s=0.8, max_future_s=0.1,
                 valid_window_s=0.5, sample_gap_s=0.45,
                 max_spatial_delta_m=0.035):
        self.max_age_s = float(max_age_s)
        self.max_future_s = float(max_future_s)
        self.valid_window_s = float(valid_window_s)
        self.sample_gap_s = float(sample_gap_s)
        self.max_spatial_delta_m = float(max_spatial_delta_m)
        self.valid_since_wall_s = None
        self.previous = None
        self.accepted = None
        self.last_reason = "NO_TARGET"
        self.goal_count = 0  # G01 does not import/use MoveIt or an ActionClient.

    def set_valid(self, valid, now_s):
        if not math.isfinite(now_s):
            self.last_reason = "INVALID_CLOCK"
            self.previous = None
            self.valid_since_wall_s = None
            return
        if not valid:
            self.valid_since_wall_s = None
            self.previous = None
            self.last_reason = "DETECTOR_INVALID"
        else:
            self.valid_since_wall_s = float(now_s)

    def accept(self, *, xyz, stamp_s, frame_id, now_s):
        if self.accepted is not None:
            self.last_reason = "ONE_SHOT_ALREADY_ACCEPTED"
            return None
        if self.valid_since_wall_s is None:
            self.previous = None
            self.last_reason = "NO_RECENT_VALID_DETECTION"
            return None
        values = (*xyz, stamp_s, now_s)
        if len(xyz) != 3 or not all(isinstance(v, (int, float)) and
                                   math.isfinite(v) for v in values):
            self.previous = None
            self.last_reason = "NONFINITE_TARGET_OR_CLOCK"
            return None
        if frame_id != "base_link":
            self.previous = None
            self.last_reason = "WRONG_FRAME"
            return None
        if stamp_s <= 0 or now_s <= 0:
            self.previous = None
            self.last_reason = "CLOCK_NOT_READY"
            return None
        if now_s - stamp_s > self.max_age_s or stamp_s - now_s > self.max_future_s:
            self.previous = None
            self.last_reason = "STALE_OR_FUTURE_STAMP"
            return None
        if now_s - self.valid_since_wall_s > self.valid_window_s or self.valid_since_wall_s > now_s:
            self.previous = None
            self.last_reason = "EXPIRED_VALIDITY"
            return None
        x, y, z = (float(v) for v in xyz)
        radius = math.hypot(x, y)
        # Geometry-admission bound only; reachable IK is a separate G03 gate.
        if not (0.15 <= radius <= 1.95 and 0.08 <= z <= 2.15):
            self.previous = None
            self.last_reason = "OUTSIDE_PRELIMINARY_WORKSPACE"
            return None
        target = Target(x, y, z, float(stamp_s))
        previous = self.previous
        if previous is None:
            self.previous = target
            self.last_reason = "FIRST_STABLE_SAMPLE_PENDING"
            return None
        gap = target.stamp_s - previous.stamp_s
        delta = math.dist((x, y, z), (previous.x, previous.y, previous.z))
        if not (0 < gap <= self.sample_gap_s and delta <= self.max_spatial_delta_m):
            self.previous = target
            self.last_reason = "INCONSISTENT_SECOND_SAMPLE"
            return None
        self.accepted = target
        self.previous = None
        self.last_reason = "READY_FOR_PLAN_ONLY"
        return target


def candidate_pregrasp(target, *, surface_to_center_z_m=0.0,
                       pregrasp_z_m=0.12):
    """Compute an illustrative Pose position, not a verified 5DOF IK solution.

    Configured offsets deliberately default to zero shape-correction; G02
    must calibrate cylinder geometry and G03 must validate orientation.
    """
    z = target.z + surface_to_center_z_m + pregrasp_z_m
    if not math.isfinite(z):
        raise ValueError("invalid TCP offset")
    return target.x, target.y, z
