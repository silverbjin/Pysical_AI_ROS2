"""Ch07 7.7 E1: test-only surface-point -> 5DOF arm joint planning targets.

The sensor PointStamped is the optical *visible surface*, not object centre.
These offsets belong exclusively to the measured G04A 24mm rod fixture.
No MoveIt/ROS imports, no joint actuation, no object teleport/attachment.
"""
from dataclasses import dataclass
import math

ARM = ("joint1", "joint2", "joint3", "joint4", "joint_wrist")
JOINT_LIMITS = {
    "joint1": (-3.14159, 3.14159),
    "joint2": (-1.57079, 1.57079),
    "joint3": (-2.0944, 2.0944),
    "joint4": (-3.14159, 3.14159),
    "joint_wrist": (-1.5708, 1.5708),
}

@dataclass(frozen=True)
class FixtureCalibration:
    # From C17 G04B measured 24mm test rod (not a general grasp model).
    source_id: str = "g04a_24mm_red_rod_test_only"
    visible_surface_to_wrist_x_m: float = -0.15
    visible_surface_to_wrist_z_m: float = -0.09
    approach_distance_m: float = 0.14
    clearance_distance_m: float = 0.07


def arm_ik_fixture(x, y, z):
    """Reused G04B 2R *position* IK; do not claim 6DOF pose IK."""
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ValueError("NONFINITE_WRIST")
    radius = math.hypot(x, y)
    dz = z - 0.6
    a, b = 0.5, 1.0  # Original Ch07 5DOF arm links.
    cos_q3 = (radius*radius + dz*dz - a*a - b*b) / (2*a*b)
    if abs(cos_q3) > 1:
        raise ValueError("UNREACHABLE_WRIST")
    q3 = math.acos(cos_q3)
    q2 = math.atan2(radius, dz) - math.atan2(b*math.sin(q3), a+b*math.cos(q3))
    values = (math.atan2(y, x), q2, q3, math.pi/2, 0.0)
    for name, value in zip(ARM, values):
        low, high = JOINT_LIMITS[name]
        if not (low <= value <= high):
            raise ValueError("JOINT_LIMIT_" + name)
    err = math.hypot(
        a*math.sin(q2)+b*math.sin(q2+q3)-radius,
        0.6+a*math.cos(q2)+b*math.cos(q2+q3)-z)
    if err > 1e-7:
        raise ValueError("IK_RESIDUAL")
    return dict(zip(ARM, values))


def fixture_plan_targets(surface_xyz, calibration=None):
    """One sensor-dependent pregrasp/stage/grasp planning candidate.

    Output is *not* approved for motion. MoveIt must check full-body
    planning scene collision and actual Gazebo world / target calibration.
    """
    c = calibration or FixtureCalibration()
    if c.source_id != "g04a_24mm_red_rod_test_only":
        raise ValueError("UNAPPROVED_FIXTURE")
    if len(surface_xyz) != 3 or not all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in surface_xyz):
        raise ValueError("INVALID_SENSOR_TARGET")
    x, y, z = (float(v) for v in surface_xyz)
    if not (0.70 <= x <= 0.91 and abs(y) <= 0.17 and 1.75 <= z <= 2.08):
        raise ValueError("TARGET_OUTSIDE_TEST_FIXTURE")
    for value in (c.visible_surface_to_wrist_x_m,
                  c.visible_surface_to_wrist_z_m,
                  c.approach_distance_m, c.clearance_distance_m):
        if not math.isfinite(value):
            raise ValueError("INVALID_CALIBRATION")
    if not (0.05 <= c.approach_distance_m <= 0.20 and
            0.02 <= c.clearance_distance_m < c.approach_distance_m):
        raise ValueError("INVALID_APPROACH")
    grasp_x = x + c.visible_surface_to_wrist_x_m
    grasp_z = z + c.visible_surface_to_wrist_z_m
    targets = (
        ("pregrasp", (grasp_x-c.approach_distance_m, y, grasp_z)),
        ("approach", (grasp_x-c.clearance_distance_m, y, grasp_z)),
        ("grasp", (grasp_x, y, grasp_z)),
    )
    return tuple({"stage": stage, "wrist_xyz_m": xyz,
                  "joints_rad": arm_ik_fixture(*xyz)}
                 for stage, xyz in targets)
