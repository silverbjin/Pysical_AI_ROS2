#!/usr/bin/env python3
"""Read-only C17 true native rod attitude: supported PLACE before OPEN feasibility.

Reference pattern: MoveIt Place → UnGrasp(open) → Retreat, but this source
check is NOT MTC/FCL, physically executed robot motion or proof of safety.
"""
import argparse
import json
import math
from pathlib import Path
from ch07_77_step1_offline_geometry import (
    C17_ARM, C17_ROD, cross, dot, wrist_source_fk)

BIN_CENTER=(0.55,0.25,1.63)
BIN_HALF=(0.15,0.15,0.10)
BIN_YAW_RAD=.35
BIN_TOP_M=1.73
C17_ROD_NATIVE_QUAT_XYZW=(.12586570861405,.02652232179323,
                          .146093726575378,.980872577298)
ROD_HALF_HEIGHT_M=.04
ROD_RADIUS_M=.012
WRIST_HALF=(.04,.03,.03)


def source_native_rod_half_height():
    x,y,z,w=C17_ROD_NATIVE_QUAT_XYZW
    n=math.sqrt(x*x+y*y+z*z+w*w)
    x,y,z,w=[v/n for v in (x,y,z,w)]
    vertical_axis=1-2*(x*x+y*y)
    return (ROD_HALF_HEIGHT_M*abs(vertical_axis)
            +ROD_RADIUS_M*math.sqrt(max(0.,1-vertical_axis**2)))


def rotated_bin_axes():
    c=math.cos(BIN_YAW_RAD);s=math.sin(BIN_YAW_RAD)
    return ((c,s,0.),(-s,c,0.),(0.,0.,1.))


def obb_sat_margin(center_a,axes_a,half_a,center_b,axes_b,half_b):
    normals=list(axes_a)+list(axes_b)
    for a in axes_a:
        for b in axes_b:
            n=cross(a,b)
            length=math.sqrt(dot(n,n))
            if length>1e-10:
                normals.append(tuple(x/length for x in n))
    delta=tuple(center_a[i]-center_b[i] for i in range(3))
    margin=-float("inf")
    for n in normals:
        r_a=sum(half_a[i]*abs(dot(a,n)) for i,a in enumerate(axes_a))
        r_b=sum(half_b[i]*abs(dot(b,n)) for i,b in enumerate(axes_b))
        margin=max(margin,abs(dot(delta,n))-r_a-r_b)
    return margin


def source_support_before_open():
    """One structural hypothesis precheck, no controller or ROS side effect."""
    center,axes,_=wrist_source_fk(C17_ARM)
    native_half_z=source_native_rod_half_height()
    rod_bottom=C17_ROD[2]-native_half_z
    support_gap=rod_bottom-BIN_TOP_M
    if not 0.10<support_gap<0.17:
        raise ValueError("C17_SOURCE_RELEASE_GAP_CHANGED")
    full_margin=obb_sat_margin(center,axes,WRIST_HALF,
                               BIN_CENTER,rotated_bin_axes(),BIN_HALF)
    # Rigid vertical translation with original C17 wrist orientation cannot
    # change the lateral geometry. Quantify first obstacle interference.
    first=None
    for j in range(2001):
        dz=j*0.0001
        c=tuple(center[i]-(dz if i==2 else 0.) for i in range(3))
        margin=obb_sat_margin(c,axes,WRIST_HALF,
                              BIN_CENTER,rotated_bin_axes(),BIN_HALF)
        if margin<=0:
            first=dz
            break
    if first is None:
        raise ValueError("SOURCE_WRIST_BIN_CLEARANCE_NOT_OBSERVED")
    blocked=(first+0.003<support_gap)
    return {
        "scope":"READ_ONLY_NATIVE_C17_SOURCE_SUPPORTED_PLACE_VS_BIN",
        "baseline":"MOVEIT_OFFICIAL_PLACE_OPEN_RETREAT_STAGE_ORDER",
        "fixture":"G04B_80MM_REAL_ROD_BIN_YAW_0.35",
        "source":"C17_Run_43800612279_same_ECS_69.542sec_original_rod_quat",
        "real_rod_xyz_m":list(C17_ROD),
        "native_rod_quaternion_xyzw":list(C17_ROD_NATIVE_QUAT_XYZW),
        "rod_vertical_projection_half_m":native_half_z,
        "rod_bottom_above_bin_top_m":support_gap,
        "original_wrist_to_bin_sat_m":full_margin,
        "first_wrist_bin_collision_downward_m":first,
        "unachieved_placement_downward_m":support_gap-first,
        "supported_place_by_C17_vertical_drop_feasible":not blocked,
        "candidate":"SIDE_OFFSET_WRIST_OUTSIDE_BIN_THEN_LOWER_TO_SUPPORT_OPEN_THEN_RETREAT",
        "candidate_status":"HYPOTHESIS_UNVERIFIED_NOT_EXECUTABLE",
        "requires":["one_fully_synchronized_physical_world_live_RGBD_G01",
                    "5DOF_full_body_FCL_and_held_rod_collision_free_joint_path",
                    "native_bilateral_grasp_retention_during_side_approach",
                    "real_support_contact_before_gripper_open",
                    "independent_zero_wrist_rod_collisions"],
        "physical_goal_authorized":False,
        "status":"STEP1_BLOCKED" if blocked else "C17_VERTICAL_PRECHECK_ONLY",
        "E2E":"BLOCKED","Ch10":"HOLD",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=source_support_before_open()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("CH07_STEP1_SUPPORTED_PLACE_VERTICAL_BLOCKED_OFFLINE_NO_GOAL")


if __name__=="__main__":
    main()
