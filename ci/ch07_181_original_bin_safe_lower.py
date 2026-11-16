"""Cycle16: ORIGINAL solid-bin collision-safe low release waypoint, offline only.

Does not alter robot/physics/bin, attach a rod, or change the accepted
release/contact/ROI tolerances. Uses the actual high-stage 5DOF joint
state and originally measured real held-rod offset. Native MoveIt FCL
plan_only MUST independently approve the goal/path before real movement.
The source 3D link4 OBB SAT is a necessary, not sufficient, preflight.
"""
import itertools
import math
from ch07_181_exact_fk import original_finger_collision_center, actual_tool_axis_angle_rad
from ch07_181_jaw_axis_carry import real_jaw_world_axis_change
from ch07_181_clearance_verified_high import valid_arm, original_link4_bin_sat_margin

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
BIN=(.55,.25)
# All these are tighter than the EXISTING high-level native release
# contract: XY<=.06m, 1.78<=Z<=1.92m, original jaw .25rad.
PREVIEW_MAX_XY_M=.055
PREVIEW_MAX_Z_M=1.915
PREVIEW_MIN_Z_M=1.80
PREVIEW_MAX_JAW_RAD=.245
PREVIEW_MAX_TOOL_RAD=.375
PREVIEW_MIN_LINK4_BIN_CLEARANCE_M=.0045
ORIGINAL_C06_SAFE_Q3_UPPER_RAD=1.05

def _bin_source_verified(scene):
    return (isinstance(scene,dict) and
            scene.get("apply_planning_scene_success") is True and
            scene.get("id")=="g04b_existing_gazebo_bin_collision" and
            scene.get("frame_id")=="base_link" and
            tuple(scene.get("center_m",()))==(.55,.25,1.63) and
            tuple(scene.get("box_m",()))==(.30,.30,.20) and
            scene.get("bin_yaw_rad")==.35 and
            scene.get("source")=="ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED")

def collision_safe_lower_target(high_actual, held_offset, scene):
    if not valid_arm(high_actual):
        raise ValueError("C16_REAL_HIGH_JOINTSTATE_INVALID")
    if (not isinstance(held_offset,(list,tuple)) or len(held_offset)!=3 or
        any(not isinstance(v,(int,float)) or not math.isfinite(v)
            for v in held_offset) or math.dist(held_offset,(0,0,0))>.055):
        raise ValueError("C16_REAL_HELD_OFFSET_INVALID")
    if not _bin_source_verified(scene):
        raise ValueError("C16_REAL_SOLID_BIN_PLANNING_SCENE_INVALID")
    if original_link4_bin_sat_margin(high_actual,bin_yaw_rad=.35)<.003:
        raise ValueError("C16_HIGH_ORIGINAL_LINK4_BIN_NOT_SEPARATED")
    off=tuple(held_offset)
    best=None
    tried=0
    # Source-stage neighbourhood only. Discrete, bounded and deterministic,
    # not an unbounded planner/physics solver sweep. q3 stays <= C06's
    # previously validated 1.05rad safe target (native stall near 1.132).
    for q2,q3,dyaw,dphi,dwrist in itertools.product(
            (-.36,-.35,-.34,-.33,-.32),
            (1.01,1.02,1.03,1.04,1.05),
            (.025,.035,.045,.055,.065),
            (.15,.17,.19,.21),
            (-.23,-.21,-.19,-.17)):
        q={"joint1":high_actual["joint1"]+dyaw,"joint2":q2,
           "joint3":q3,"joint4":high_actual["joint4"]+dphi,
           "joint_wrist":high_actual["joint_wrist"]+dwrist}
        if not (-3.14159<q["joint1"]<3.14159 and
                -1.57079<q2<1.57079 and -2.0944<q3<=ORIGINAL_C06_SAFE_Q3_UPPER_RAD and
                -3.14159<q["joint4"]<3.14159 and
                -1.5708<q["joint_wrist"]<1.5708):
            continue
        tried+=1
        center=original_finger_collision_center(q)
        rod=[center[i]+off[i] for i in range(3)]
        xy=math.hypot(rod[0]-BIN[0],rod[1]-BIN[1])
        if xy>PREVIEW_MAX_XY_M or not PREVIEW_MIN_Z_M<=rod[2]<=PREVIEW_MAX_Z_M:
            continue
        jaw=real_jaw_world_axis_change(high_actual,q)
        if jaw>PREVIEW_MAX_JAW_RAD:
            continue
        tool=actual_tool_axis_angle_rad(high_actual,q)
        if tool>PREVIEW_MAX_TOOL_RAD:
            continue
        sep=original_link4_bin_sat_margin(q,bin_yaw_rad=.35)
        if sep<PREVIEW_MIN_LINK4_BIN_CLEARANCE_M:
            continue
        # A straight joint interpolation is an ADDITIONAL prefilter, not
        # MoveIt/FCL path certification. This tests 9 bounded states.
        straight_min=min(
            original_link4_bin_sat_margin(
                {n:high_actual[n]+t*(q[n]-high_actual[n]) for n in ARM},
                bin_yaw_rad=.35)
            for t in (0,.125,.25,.375,.5,.625,.75,.875,1.0))
        if straight_min<.003:
            continue
        # Balance existing release headroom in XY, Z, jaw and collision.
        score=min((PREVIEW_MAX_XY_M-xy)/.01,
                  (PREVIEW_MAX_Z_M-rod[2])/.01,
                  (PREVIEW_MAX_JAW_RAD-jaw)/.03,
                  (sep-PREVIEW_MIN_LINK4_BIN_CLEARANCE_M)/.005)
        if best is None or score>best[0]:
            best=(score,q,rod,xy,jaw,tool,sep,straight_min)
    if best is None:
        raise ValueError("C16_NO_COLLISION_SAFE_REAL_BIN_LOWER_GOAL")
    score,q,rod,xy,jaw,tool,sep,straight_min=best
    return {"target":q,"predicted_rod_world_xyz_m":rod,
            "predicted_bin_xy_error_m":xy,
            "predicted_release_drop_m":rod[2]-(1.73+.08/2),
            "world_jaw_change_rad":jaw,
            "world_tool_change_rad":tool,
            "original_solid_bin_link4_sat_clearance_m":sep,
            "preview_min_link4_bin_clearance_m":straight_min,
            "candidates_checked":tried,
            "balanced_headroom_score":score,
            "source_high_actual_jointstate":dict(high_actual),
            "source_original_real_held_rod_offset_m":list(off),
            "single_factor":"LOWER_JOINT_GOAL_ONLY",
            "requires_independent_moveit_plan_only_before_real_goal":True,
            "scope":"KINEMATIC_ONLY_NOT_PHYSICAL_ACCEPTANCE"}
