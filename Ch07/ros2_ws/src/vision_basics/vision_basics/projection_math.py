"""Pure pinhole back-projection with explicit metric depth (ROS-independent)."""
import math


def back_project(u, v, z_m, fx, fy, cx, cy, min_depth=0.1, max_depth=5.0):
    values = (u, v, z_m, fx, fy, cx, cy, min_depth, max_depth)
    if not all(math.isfinite(float(x)) for x in values):
        raise ValueError("non-finite pixel/calibration/depth")
    if fx <= 0 or fy <= 0 or min_depth <= 0 or max_depth <= min_depth:
        raise ValueError("invalid intrinsics or depth range")
    if not min_depth <= z_m <= max_depth:
        raise ValueError("missing or out-of-range depth")
    return ((u - cx) * z_m / fx, (v - cy) * z_m / fy, float(z_m))
