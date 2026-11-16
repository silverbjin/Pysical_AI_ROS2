"""Cycle13: actual held-offset adaptive high target for the existing C12 bin.

Only the 5DOF high Goal selector changes. The original solid Gazebo bin
(0.30 x 0.30 x 0.20 m, centre [0.55,0.25,1.63], yaw=.35 rad) and
original link4 OBB remain intact. Native source-derived held offset is
read after real grip/hold, not substituted with a frozen reference.
Pure Python bounded geometry is a candidate; official MoveIt plan_only
MUST pass before any physical high motion. Never claim G04B from L0.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center,actual_tool_axis_angle_rad
from ch07_181_jaw_axis_carry import real_jaw_world_axis_change
from ch07_181_high_goal_precision_contract import (
    HIGH_FK_BIN_TARGET_MAX_ERROR_M,assess_precise_high_arrival)
from ch07_181_clearance_verified_high import (
    valid_arm,original_link4_bin_sat_margin)

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
SEED=(.45513094,.00642095,.57534782,1.41250335,-.18389185)
BIN=(.55,.25)
MIN_ORIGINAL_SOLID_BIN_CLEARANCE_M=.003
MAX_WORLD_JAW_CHANGE_RAD=.25
MAX_TOOL_AXIS_CHANGE_RAD=.38

def _exact_xy_from_measured_offset(seed,offset):
    """Solve only source q1/q3 for exact bin XY, no physics or planner."""
    q=dict(zip(ARM,seed))
    for _ in range(8):
        p=original_finger_collision_center(q)
        ex=BIN[0]-p[0]-offset[0]
        ey=BIN[1]-p[1]-offset[1]
        if math.hypot(ex,ey)<1e-8:
            break
        h=1e-5
        a=original_finger_collision_center({**q,"joint1":q["joint1"]+h})
        b=original_finger_collision_center({**q,"joint3":q["joint3"]+h})
        aa=(a[0]-p[0])/h;bb=(b[0]-p[0])/h
        cc=(a[1]-p[1])/h;dd=(b[1]-p[1])/h
        det=aa*dd-bb*cc
        if not math.isfinite(det) or abs(det)<1e-9:
            raise ValueError("C13_BIN_XY_JACOBIAN_SINGULAR")
        q["joint1"]+=max(-.08,min(.08,(dd*ex-bb*ey)/det))
        q["joint3"]+=max(-.08,min(.08,(-cc*ex+aa*ey)/det))
    return q

def source_bin_rotated_high_goal(held,rod,scene):
    if not valid_arm(held) or not isinstance(rod,(list,tuple)) or len(rod)!=3:
        raise ValueError("C13_HELD_INPUT_INVALID")
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in rod):
        raise ValueError("C13_NONFINITE_ROD")
    if (not isinstance(scene,dict) or scene.get("apply_planning_scene_success") is not True
        or scene.get("id")!="g04b_existing_gazebo_bin_collision"
        or scene.get("frame_id")!="base_link"
        or tuple(scene.get("center_m",()))!=(.55,.25,1.63)
        or tuple(scene.get("box_m",()))!=(.30,.30,.20)
        or scene.get("bin_yaw_rad")!=.35
        or scene.get("source")!="ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED"):
        raise ValueError("C13_STATIC_SCENE_ROLL_PITCH_SHAPE_OR_YAW_MISMATCH")
    f=original_finger_collision_center(held)
    offset=[rod[k]-f[k] for k in range(3)]
    if math.sqrt(sum(v*v for v in offset))>.055:
        raise ValueError("C13_NOT_REAL_HELD_ROD")

    # Source-derived bounded candidate family, not an arbitrary IK/solver
    # sweep. q2, q4, wrist define ONLY the high target posture. For each,
    # align XY with actual held rod offset, then admit small pose perturbations
    # only if all unchanged original collision + 5mm + world jaw gates pass.
    best=None
    tested=0
    for q2 in (.0,.004,.008,.012,.016):
        # Cycle14: the original C13 narrow q4/wrist seeds silently assumed
        # one old held jaw direction. Original native C13 lift feedback had
        # q4≈1.548rad, unlike earlier 1.60rad. Broaden ONLY target-posture
        # candidates; no accepted geometry, contact or goal gate changes.
        # Fixed finite grid: no scipy/random solver or Gazebo calls here.
        for i in range(26):
            q4=1.250+.010*i
            for j in range(10):
                wrist=-.255+.020*j
                try:
                    aligned=_exact_xy_from_measured_offset(
                        (SEED[0],q2,SEED[2],q4,wrist),offset)
                except ValueError:
                    continue
                for dyaw in (-.003,0.,.003):
                    for dq3 in (-.009,-.006,-.003,0.,.003,.006,.009):
                        q=dict(aligned)
                        q["joint1"]+=dyaw
                        q["joint3"]+=dq3
                        if (abs(q["joint1"]-SEED[0])>.10
                            or not .35<q["joint3"]<.90):
                            continue
                        tested+=1
                        p=original_finger_collision_center(q)
                        predicted=[p[k]+offset[k] for k in range(3)]
                        xy=math.hypot(predicted[0]-BIN[0],
                                      predicted[1]-BIN[1])
                        if (xy>HIGH_FK_BIN_TARGET_MAX_ERROR_M
                            or predicted[2]<1.98):
                            continue
                        jaw=real_jaw_world_axis_change(held,q)
                        if jaw>MAX_WORLD_JAW_CHANGE_RAD:
                            continue
                        tool=actual_tool_axis_angle_rad(held,q)
                        if tool>MAX_TOOL_AXIS_CHANGE_RAD:
                            continue
                        margin=original_link4_bin_sat_margin(
                            q,bin_yaw_rad=.35)
                        if margin<MIN_ORIGINAL_SOLID_BIN_CLEARANCE_M:
                            continue
                        # Prefer independent headroom in ALL three gates,
                        # rather than blindly maximizing one SAT clearance.
                        score=min(
                            (margin-MIN_ORIGINAL_SOLID_BIN_CLEARANCE_M)/.002,
                            (HIGH_FK_BIN_TARGET_MAX_ERROR_M-xy)/.002,
                            (MAX_WORLD_JAW_CHANGE_RAD-jaw)/.012)
                        if best is None or score>best[0]:
                            best=(score,q,predicted,xy,jaw,tool,margin)
    if best is None:
        raise ValueError("C13_NO_SAFE_HIGH_GOAL_FOR_ACTUAL_HELD_OFFSET")
    score,q,predicted,xy,jaw,tool,margin=best
    if not assess_precise_high_arrival(q,q,offset)["real_arm_tracking_scoped_pass"]:
        raise ValueError("C13_SOURCE_STRICT_5MM_ORACLE_FAILED")
    return {"joint_goal":q,"predicted_rod_xyz_m":predicted,
        "strict_bin_xy_error_m":xy,"jaw_world_change_rad":jaw,
        "tool_axis_change_rad":tool,"real_rotated_bin_sat_margin_m":margin,
        "bounded_candidates_checked":tested,
        "minimum_balanced_headroom_score":score,
        "world_single_factor":"C13_ADAPTIVE_HIGH_GOAL_IN_UNCHANGED_C12_REAL_BIN",
        "requires_moveit_plan_only_before_real_motion":True,
        "G04B":"BLOCKED_UNTIL_NATIVE_CONTACT_RELEASE_ROI_PASS"}
