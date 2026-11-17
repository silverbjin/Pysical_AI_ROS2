#!/usr/bin/env python3
"""Read-only C17 source geometry: reject a wrist OUTSIDE-BIN XY footprint
while holding the 80mm rod inside the accepted 9cm placement ROI.

This is a necessary-condition proof for this ONE proposed strategy, not
an exhaustive impossibility theorem for all 5DOF grasp/place/release poses.
No ROS/MoveIt imports, no Gazebo commands, no motor Goals or object changes.
"""
import argparse
import json
import math
from pathlib import Path
from ch07_77_step1_offline_geometry import C17_ARM, C17_ROD, wrist_source_fk

# Native C17 run 43800612279 (pre-release sim time 69.542 s).
# Real source collision wrist OBB 0.08 x 0.06 x 0.06 m.
BIN_BOX_HALF_XY_M = 0.15    # original 0.30 x 0.30 m solid bin, yaw .35 rad
BIN_YAW_RAD = 0.35
BIN_CENTER_XY_M = (0.55, 0.25)
MAX_SETTLED_BIN_XY_ERROR_M = 0.09  # immutable physical acceptance
WRIST_HALF_EXTENTS_M = (0.04, 0.03, 0.03)


def side_outside_necessary_condition(arm=None, rod=None):
    """A disjoint wrist/bin XY projection needs at least 0.18m radial reach.

    For ANY separating horizontal unit axis:
      solid bin projection halfwidth =
          .15*(abs(dot(axis, rotated-bin-X))
               +abs(dot(axis, rotated-bin-Y))) >= .15m.
      wrist OBB horizontal projected halfwidth >= min(.04,.03,.03)=.03m.
      wrist centre relative to bin centre <= rod ROI .09m +
          native rod-to-wrist-centre distance .08434057m, if the object is
          held rigidly with that measured centre offset.

    Thus .17434 < .180 and there can be NO separating horizontal axis
    for the wrist entirely OUTSIDE the horizontal bin footprint under
    the fixed no-slip grasp geometry. This does NOT prove 3D collision:
    z-separated wrists or a different grip shape are outside this scope.
    """
    arm = dict(C17_ARM if arm is None else arm)
    rod = tuple(C17_ROD if rod is None else rod)
    if set(arm) != set(C17_ARM) or len(rod) != 3 or not all(
        isinstance(v, (float, int)) and math.isfinite(v)
        for v in (*arm.values(), *rod)
    ):
        raise ValueError("C17_NATIVE_GRASP_SOURCE_INVALID")

    # wrist_source_fk already returns the +0.03m-local-Z OBB centre.
    wrist_center, _wrist_axes, _ = wrist_source_fk(arm)
    native_rod_to_wrist_m = math.dist(rod, wrist_center)
    most_wrist_centre_from_bin_m = (
        MAX_SETTLED_BIN_XY_ERROR_M + native_rod_to_wrist_m
    )
    minimum_disjoint_radius_m = (
        BIN_BOX_HALF_XY_M + min(WRIST_HALF_EXTENTS_M)
    )
    shortfall_m = minimum_disjoint_radius_m - most_wrist_centre_from_bin_m
    safe_to_authorize = shortfall_m <= 0  # necessary only; still no full FCL

    return {
        "scope": "C17_FIXED_GRIP_2D_OUTSIDE_BIN_NECESSARY_CONDITION_ONLY",
        "source_run": 43800612279,
        "source_sim_time_s_approx": 69.542,
        "bin_yaw_rad": BIN_YAW_RAD,
        "bin_center_xy_m": list(BIN_CENTER_XY_M),
        "native_rod_xyz_m": list(rod),
        "native_wrist_box_center_xyz_m": list(wrist_center),
        "native_rod_to_wrist_box_center_distance_m": native_rod_to_wrist_m,
        "bin_roi_radial_max_m": MAX_SETTLED_BIN_XY_ERROR_M,
        "max_wrist_center_distance_from_bin_m": most_wrist_centre_from_bin_m,
        "necessary_wrist_footprint_separation_distance_m": minimum_disjoint_radius_m,
        "minimum_unachievable_horizontal_separation_m": max(0.0, shortfall_m),
        "fixed_native_grip_outside_xy_feasible": safe_to_authorize,
        "not_proven": [
            "arbitrary arm motion and nonrigid object slip",
            "new tool down-pointing or alternate grasp from above",
            "3D collision-free pose with wrist completely ABOVE bin",
            "valid dynamic 5DOF/jaw FCL path and native bilateral contact",
        ],
        "physical_goal_authorized": False,
        "candidate_status": (
            "NECESSARY_XY_ONLY_NOT_SAFE_FOR_MOTION"
            if safe_to_authorize else
            "REJECT_FIXED_C17_GRIP_WRIST_OUTSIDE_BIN_XY"
        ),
        "status": "STEP1_BLOCKED",
        "step2_motor_e2e": "NOT_RUN",
        "owner_wsl2": "NOT_READY",
        "Ch10": "HOLD",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = side_outside_necessary_condition()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("CH07_STEP1_C17_SIDE_OUTSIDE_BIN_XY_REJECTED_NO_MOTOR_GOALS")


if __name__ == "__main__":
    main()
