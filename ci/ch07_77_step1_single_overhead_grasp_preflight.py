#!/usr/bin/env python3
"""ONE source-bounded overhead 5DOF grasp -> supported place preflight.

Nominal hypothesis: upright 80mm G04B rod gripped with tool +Z vertically
DOWN and jaw X horizontal, finger contact centre at the rod centre.
Open only after placement on the ORIGINAL yaw=0.35 real solid bin.

No search, tuning, motor/MoveIt Goal, new world, fake rod attach or teleport.
This checks original 2R position IK, joint wrist limits and wrist/link4/bin
OBB collision necessary conditions. If RED, full-body FCL is NOT_REQUESTED:
an out-of-range joint Goal must never be passed to MoveIt as a success.
"""
import argparse
import json
import math
from pathlib import Path
from ch07_77_step1_offline_geometry import wrist_source_fk
from ch07_77_step1_supported_release_preflight import (
    BIN_CENTER, BIN_HALF, WRIST_HALF, obb_sat_margin, rotated_bin_axes
)

# Existing original URDF: shoulder world z=0.6, 2R arm 0.5m + 1m.
# The finger1/finger2 local collision centre is tool +Z 0.10m
# (ci/ch07_181_exact_fk.py from physical PR202).
L1_M = 0.5
L2_M = 1.0
SHOULDER_Z_M = 0.6
FINGER_CONTACT_LOCAL_Z_M = 0.1
LINK4_HALF = (0.025, 0.025, 0.25)  # original link4 0.05x0.05x0.5 m
JOINT_LIMITS = {
    "joint1": (-3.14159, 3.14159),
    "joint2": (-1.57079, 1.57079),
    "joint3": (-2.0944, 2.0944),
    "joint4": (-3.14159, 3.14159),
    "joint_wrist": (-1.5708, 1.5708),
}
ROD_PICK_CENTER = (0.70, 0.0, 1.94)  # real G04B 80mm rod world
BIN_ROD_SUPPORTED_CENTER = (0.55, 0.25, 1.73 + 0.08/2)
CANDIDATE_NAME = "ONE_VERTICAL_DOWN_TOOL_HORIZONTAL_JAW_OVERHEAD_PICK_PLACE"
FCL_GATE = "NOT_REQUESTED_PRE_FCL_HARD_REJECT"


def link4_source_fk(q):
    """Literal C10 source geometry from PR202, no MoveIt substitute."""
    yaw, q2, phi = q["joint1"], q["joint2"], q["joint4"]
    theta = q2 + q["joint3"]
    cy, sy = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(theta), math.sin(theta)
    cp, sp = math.cos(phi), math.sin(phi)
    axes = (
        (cy*ct*cp-sy*sp, sy*ct*cp+cy*sp, -st*cp),
        (-cy*ct*sp-sy*cp, -sy*ct*sp+cy*cp, st*sp),
        (cy*st, sy*st, ct),
    )
    r = 0.5*math.sin(q2) + 0.75*math.sin(theta)
    centre = (r*cy, r*sy, 0.6 + 0.5*math.cos(q2) + 0.75*math.cos(theta))
    return centre, axes


def overhead_2r_ik(rod_center):
    """Exactly one vertical tool-down wrist/TCP pose and its two IK branches.

    At tool DOWN: original finger centre is 0.10m BELOW the wrist origin.
    The original +Z tool orientation is DOWN when joint4=0 and
    theta + joint_wrist = pi. Positive/negative elbow branches are the two
    analytic inverses of this SAME pose, not additional grasp candidates.
    """
    x, y, z = rod_center
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in rod_center):
        raise ValueError("NONFINITE_CANDIDATE_ROD")
    wx, wy, wz = x, y, z + FINGER_CONTACT_LOCAL_Z_M
    radius = math.hypot(wx, wy)
    dz = wz - SHOULDER_Z_M
    d = math.hypot(radius, dz)
    if d > L1_M + L2_M + 1e-9 or d < abs(L2_M-L1_M)-1e-9:
        return {"reachable":False, "wrist_origin_m":[wx,wy,wz],
                "shoulder_to_wrist_m":d, "max_reach_m":L1_M+L2_M,
                "ik_branches":[]}
    cos_q3 = (radius**2 + dz**2 - L1_M**2 - L2_M**2)/(2*L1_M*L2_M)
    q3_pos = math.acos(max(-1.,min(1.,cos_q3)))
    q1 = math.atan2(wy, wx)
    branches = []
    for branch, q3 in (("positive",q3_pos),("negative",-q3_pos)):
        q2 = math.atan2(radius,dz) - math.atan2(
            L2_M*math.sin(q3), L1_M + L2_M*math.cos(q3))
        theta=q2+q3
        # Exact downward tool +Z and horizontal jaw X, joint4 fixed at 0.
        q = dict(joint1=q1,joint2=q2,joint3=q3,joint4=0.0,
                 joint_wrist=math.pi-theta)
        # q_wrist is NOT clipped; a clipped angle would NOT be this candidate.
        wrist, axes, finger=wrist_source_fk(q)
        limits={name:lower<=q[name]<=upper for name,(lower,upper) in JOINT_LIMITS.items()}
        wrist_origin = tuple(
            finger[i] - FINGER_CONTACT_LOCAL_Z_M*axes[2][i]
            for i in range(3))
        # Original source FK and requested rod contact must agree.
        if math.dist(finger,rod_center)>1e-7 or math.dist(
            wrist_origin,(wx,wy,wz))>1e-7:
            raise ValueError("CANDIDATE_SOURCE_FK_NOT_MATCHED")
        if abs(axes[0][2])>1e-7 or abs(axes[2][2]+1)>1e-7:
            raise ValueError("OVERHEAD_ORIENTATION_NOT_VERTICAL")
        link4_center,link4_axes=link4_source_fk(q)
        collision=dict(
            wrist_bin_sat_margin_m=obb_sat_margin(
                wrist,axes,WRIST_HALF,BIN_CENTER,rotated_bin_axes(),BIN_HALF),
            link4_bin_sat_margin_m=obb_sat_margin(
                link4_center,link4_axes,LINK4_HALF,
                BIN_CENTER,rotated_bin_axes(),BIN_HALF))
        branches.append({
            "elbow_branch":branch,"arm_goal_rad":q,
            "theta_rad":theta,
            "required_wrist_rad":q["joint_wrist"],
            "wrist_upper_limit_rad":JOINT_LIMITS["joint_wrist"][1],
            "wrist_over_limit_rad":max(0.0,q["joint_wrist"]-JOINT_LIMITS["joint_wrist"][1]),
            "joints_within_original_urdf_limits":all(limits.values()),
            "joint_limit_ok":limits,
            "nominal_vertical_tool_down":True,
            "nominal_jaw_horizontal":True,
            "finger_world_m":list(finger),
            "link4_box_world_m":list(link4_center),
            "collision_preview":collision,
            "collision_preview_note":"SAT is necessary, not MoveIt FCL or native physics",
        })
    return {"reachable":True,"wrist_origin_m":[wx,wy,wz],
            "shoulder_to_wrist_m":d,"max_reach_m":L1_M+L2_M,
            "ik_branches":branches}


def report_one_overhead_candidate():
    pick=overhead_2r_ik(ROD_PICK_CENTER)
    place=overhead_2r_ik(BIN_ROD_SUPPORTED_CENTER)
    if not place["reachable"]:
        raise ValueError("UNEXPECTED_PLACE_POSITION_UNREACHABLE")
    main=place["ik_branches"][0]
    pick_ok=pick["reachable"]
    place_limits_ok=any(b["joints_within_original_urdf_limits"]
                        for b in place["ik_branches"])
    place_collision_preview_ok=any(
        b["collision_preview"]["wrist_bin_sat_margin_m"]>=0.003
        and b["collision_preview"]["link4_bin_sat_margin_m"]>=0.003
        for b in place["ik_branches"])
    # Hard fail-closed: FCL may only run on an actually reachable,
    # within-limits and source-collision-free candidate (not this one).
    allowed_to_plan=pick_ok and place_limits_ok and place_collision_preview_ok
    if allowed_to_plan:
        raise ValueError("UNEXPECTED_READY_NEEDS_SINGLE_MOVEIT_FCL_REVIEW")
    return {
        "scope":"ONE_5DOF_OVERHEAD_VERTICAL_TOOL_HORIZONTAL_JAW_SOURCE_ONLY",
        "candidate":CANDIDATE_NAME,
        "baseline":"MOVEIT_OFFICIAL_PLACE_OPEN_RETREAT_STAGE_ORDER",
        "physical_source":"G04B_80MM_SAME_WORLD_REAL_RGBD_G01_CI_43984345894",
        "original_rod_pick_xyz_m":list(ROD_PICK_CENTER),
        "original_bin_rod_supported_xyz_m":list(BIN_ROD_SUPPORTED_CENTER),
        "original_physical_bin_yaw_rad":0.35,
        "rod_mass_kg":0.05,
        "geometry_assumption":"new vertical grip at original finger collision centre; no fake attachment",
        "pickup_ik":pick,
        "supported_place_ik":place,
        "primary_place_elbow":main["elbow_branch"],
        "pickup_position_reachable":pick_ok,
        "supported_place_within_joint_limits":place_limits_ok,
        "supported_place_source_collision_clear":place_collision_preview_ok,
        "moveit_fcl_plan_only":FCL_GATE,
        "moveit_plan_only_goals_sent":0,
        "motor_goals_sent":0,
        "collision_criterion_unchanged":True,
        "candidate_status":"REJECTED_PRE_FCL_HARD_GEOMETRY",
        "status":"STEP1_BLOCKED",
        "G04B_PHYSICAL_CLEAN":"BLOCKED",
        "CH07_77_E2E":"BLOCKED",
        "E2_REAL_RGBD_TO_MOVEIT_PLAN_ONLY":"SCOPED_PASS_PRIOR_NOT_RERUN",
        "G04B_SHORT_WORLD_RGBD_G01":"SCOPED_PASS_PRIOR_NOT_RERUN",
        "Owner_WSL2":"NOT_READY",
        "Ch10":"HOLD",
        "not_proven":["arbitrary orientations or alternative regrasp",
                      "MoveIt FCL for any feasible alternative",
                      "actual native grasp/hold/release and zero forbidden contact"],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=report_one_overhead_candidate()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")
    print("CH07_77_SINGLE_OVERHEAD_GRASP_REJECTED_PRE_FCL_NO_ROS_NO_GOAL")


if __name__=="__main__":
    main()
