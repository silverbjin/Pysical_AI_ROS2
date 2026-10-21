"""ROS-independent front-sector analysis for book section 11.3.4."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SectorResult:
    state: str
    reason: str
    min_distance: float | None
    sector_count: int
    valid_count: int
    invalid_count: int
    coverage_complete: bool


def analyze_front_sector(ranges, angle_min, angle_increment, range_min, range_max,
                         safe_distance=0.5, scope_deg=30.0):
    """Analyze sensor-frame +/-scope_deg around +X. This does not command braking."""
    values = (angle_min, angle_increment, range_min, range_max, safe_distance, scope_deg)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Scan metadata and parameters must be finite')
    if angle_increment == 0 or abs(angle_increment) > 2*math.pi:
        raise ValueError('Invalid angle_increment')
    if range_min < 0 or range_max <= range_min:
        raise ValueError('Invalid sensor range limits')
    if safe_distance <= 0 or not 0 < scope_deg <= 180:
        raise ValueError('Invalid distance or sector half-angle')
    scope = math.radians(scope_deg)
    angles, valid = [], []
    invalid = 0
    for index, distance in enumerate(ranges):
        angle = angle_min + index*angle_increment
        angle = math.atan2(math.sin(angle), math.cos(angle))
        if abs(angle) > scope + 1e-7:
            continue
        angles.append(angle)
        if (math.isfinite(distance) and distance > 0 and
                range_min <= distance <= range_max):
            valid.append(float(distance))
        else:
            invalid += 1
    angles.sort()
    step = abs(angle_increment) + 1e-7
    coverage = bool(angles) and (
        angles[0] <= -scope+step and angles[-1] >= scope-step and
        all(b-a <= step for a, b in zip(angles, angles[1:])))
    nearest = min(valid) if valid else None
    if nearest is not None and nearest <= safe_distance:
        state, reason = 'OBSTACLE', 'close_return'
    elif nearest is None:
        state, reason = 'UNKNOWN', 'no_valid_returns'
    elif invalid:
        state, reason = 'UNKNOWN', 'invalid_returns_in_sector'
    elif not coverage:
        state, reason = 'UNKNOWN', 'partial_sector_coverage'
    else:
        state, reason = 'CLEAR', 'valid_returns_beyond_threshold'
    return SectorResult(state, reason, nearest, len(angles), len(valid), invalid, coverage)


def scan_is_fresh(stamp, ros_now, received_steady, steady_now, timeout):
    """Check both acquisition delay and wall-time silence, including simulation pause."""
    if stamp is None or received_steady is None:
        return False
    values = (stamp, ros_now, received_steady, steady_now, timeout)
    if not all(math.isfinite(v) for v in values) or timeout <= 0:
        return False
    return -0.1 <= ros_now-stamp <= timeout and 0 <= steady_now-received_steady <= timeout
