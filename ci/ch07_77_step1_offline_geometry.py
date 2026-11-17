#!/usr/bin/env python3
"""Ch07 §7.7 Step 1: read-only, source-bounded physical integration gate.

Compare G04A/G04B *different* fixtures, then re-evaluate Cycle17's actual
pre-release wrist against the falling rod AABB using the original 5DOF FK.
The bounded 4-joint diagnostic is NOT a physics simulation, full IK/FCL,
collision-free proof, or authorization to send a MoveIt/arm/gripper Goal.
"""
import argparse
import itertools
import json
import math
from pathlib import Path

# Exact source snapshots: G04A main 9431fb5, G04B PR202 96d4f4d,
# native pre-release arm+rod from G04B C17 Run 43800612279.
G04A = dict(rod_x_m=0.80, rod_height_m=0.24, support_top_m=1.82,
            robot_spawn_z_m=0.05, bin_yaw_rad=0.0)
G04B = dict(rod_x_m=0.70, rod_height_m=0.08, support_top_m=1.90,
            robot_spawn_z_m=0.0, bin_yaw_rad=0.35)
C17_ARM = dict(joint1=0.509164, joint2=-0.331197,
               joint3=1.049568, joint4=1.569168,
               joint_wrist=-0.346061)
C17_ROD = (0.503606, 0.238149, 1.91499)
ARM = tuple(C17_ARM)
C17_RUN = 43800612279


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def angle(a, b):
    return math.acos(max(-1., min(1., dot(a, b))))


def wrist_source_fk(q):
    """Exact original Rz(q1) Ry(q2+q3) Rz(q4) Ry(qw) source chain."""
    yaw = q["joint1"]
    theta = q["joint2"] + q["joint3"]
    phi, w = q["joint4"], q["joint_wrist"]
    ct, st = math.cos(theta), math.sin(theta)
    cp, sp = math.cos(phi), math.sin(phi)
    cw, sw = math.cos(w), math.sin(w)
    # Opposing jaw X and tool Z expressed in world frame.
    jx, jy, jz = ct*cp*cw-st*sw, sp*cw, -st*cp*cw-ct*sw
    zx, zy, zz = ct*cp*sw+st*cw, sp*sw, -st*cp*sw+ct*cw
    cy, sy = math.cos(yaw), math.sin(yaw)
    jaw = (jx*cy-jy*sy, jx*sy+jy*cy, jz)
    tool = (zx*cy-zy*sy, zx*sy+zy*cy, zz)
    axes = (jaw, cross(tool, jaw), tool)
    radial = 0.5*math.sin(q["joint2"]) + math.sin(theta)
    origin = (radial*cy, radial*sy,
              0.6 + 0.5*math.cos(q["joint2"]) + math.cos(theta))
    # Original wrist OBB centre is at +0.03m local Z; finger centre at 0.10m.
    center = tuple(origin[i] + 0.03*tool[i] for i in range(3))
    finger = tuple(origin[i] + 0.10*tool[i] for i in range(3))
    return center, axes, finger


def wrist_falling_rod_sat_margin(q, rod):
    """Cycle18 source OBB vs conservative vertical drop AABB, in metres.

    Positive is separating, negative is overlap *of the conservative boxes*.
    A positive value alone does not certify a safe physical/MoveIt path.
    """
    if set(q) != set(ARM) or len(rod) != 3 or not all(
            math.isfinite(float(v)) for v in (*q.values(), *rod)):
        raise ValueError("INVALID_SOURCE_ARM_OR_ROD")
    center, axes, _ = wrist_source_fk(q)
    drop = max(0., rod[2] - 1.77)
    rod_center = (rod[0], rod[1], rod[2] - drop/2)
    rod_half = (0.028, 0.028, 0.04 + drop/2)
    world = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
    normals = list(axes) + list(world)
    for a in axes:
        for b in world:
            normal = cross(a, b)
            magnitude = math.sqrt(dot(normal, normal))
            if magnitude > 1e-10:
                normals.append(tuple(v/magnitude for v in normal))
    delta = tuple(rod_center[i]-center[i] for i in range(3))
    margin = -float("inf")
    for n in normals:
        wr = sum(size*abs(dot(a, n)) for a, size
                 in zip(axes, (0.04, 0.03, 0.03)))
        rr = sum(size*abs(dot(a, n)) for a, size
                 in zip(world, rod_half))
        margin = max(margin, abs(dot(delta, n))-wr-rr)
    return margin


def offline_report():
    original_center, original_axes, finger = wrist_source_fk(C17_ARM)
    offset = tuple(C17_ROD[i]-finger[i] for i in range(3))
    baseline = wrist_falling_rod_sat_margin(C17_ARM, C17_ROD)
    count = 0
    best = None

    # Deliberately *bounded* neighborhood of C17 already-accepted lower
    # state. The held offset is approximated as constant in world; this
    # screening assumption is NOT physically certified under rotation.
    for d2, d3, d4, dw in itertools.product(
            range(-12, 13, 2), range(-12, 1, 2),
            range(-20, 21, 4), range(-25, 26, 5)):
        q = dict(C17_ARM, joint2=C17_ARM["joint2"]+d2/100.,
                 joint3=C17_ARM["joint3"]+d3/100.,
                 joint4=C17_ARM["joint4"]+d4/100.,
                 joint_wrist=C17_ARM["joint_wrist"]+dw/100.)
        _, axes, f = wrist_source_fk(q)
        rod = tuple(f[i]+offset[i] for i in range(3))
        xy = math.hypot(rod[0]-0.55, rod[1]-0.25)
        if xy > 0.06 or not 1.78 <= rod[2] <= 1.92:
            continue
        jaw = angle(axes[0], original_axes[0])
        tool = angle(axes[2], original_axes[2])
        if jaw > 0.245 or tool > 0.375:
            continue
        count += 1
        margin = wrist_falling_rod_sat_margin(q, rod)
        if best is None or margin > best["sat_margin_m"]:
            best = dict(sat_margin_m=margin, q2_delta_rad=d2/100.,
                        q3_delta_rad=d3/100., q4_delta_rad=d4/100.,
                        qw_delta_rad=dw/100., predicted_rod_xyz_m=rod,
                        bin_xy_m=xy, jaw_change_rad=jaw,
                        tool_change_rad=tool)
    mismatches = {
        name: {"vision_g04a": G04A[name], "physical_g04b": G04B[name]}
        for name in G04A if G04A[name] != G04B[name]
    }
    safe = best is not None and best["sat_margin_m"] >= 0.008
    # Safe candidate cannot be accepted even with SAT if the two fixtures
    # remain incompatible and full-body FCL+native physical evidence absent.
    return {
        "scope": "READ_ONLY_C17_SOURCE_BOUNDED_GEOMETRY_NOT_MOVEIT_NOT_PHYSICS",
        "status": "STEP1_BLOCKED",
        "actual_g04a_e2": "SCOPED_PASS_NOT_RERUN",
        "physical_c17_run": C17_RUN,
        "fixture_mismatches": mismatches,
        "c17_wrist_drop_sat_m": baseline,
        "bounded_sample_count": count,
        "best_bounded_sample": best,
        "bounded_collision_free_candidate_found": safe,
        "unverified": ["short_80mm_rod_live_camera_detection",
                       "same_world_base_link_and_camera_frame",
                       "actual_rod_to_tcp_calibration",
                       "actual_gripped_rod_motion_under_new_arm_pose",
                       "MoveIt_full_body_FCL_plan_only",
                       "same_session_native_contact_and_zero_wrist_collision"],
        "physics_goal_authorized": False,
        "step2_e2e_l2": "NOT_RUN",
        "owner_wsl2": "NOT_READY",
        "Ch10": "HOLD",
        "warning": ("Limited static sample; cannot establish impossibility of "
                    "other grasp/release strategies. Never convert static "
                    "margin or a nominal FJT result to physical PASS.")
    }


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--out", type=Path, required=True)
    cfg = args.parse_args()
    report = offline_report()
    cfg.out.parent.mkdir(parents=True, exist_ok=True)
    cfg.out.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print("CH07_77_STEP1_OFFLINE_SOURCE_REVIEW_BLOCKED_NO_MOTOR_GOALS")


if __name__ == "__main__":
    main()
