#!/usr/bin/env python3
"""Issue #181: validate a real MoveIt planned arm trajectory for direct ros2_control FJT.

The MoveGroup execution path is deliberately not used for the test-only physical
G04B candidate because it has reproduced a frozen finger even in an empty world.
This contract never fakes success or bypasses MoveIt collision planning.
"""
import math

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
DIRECT_FJT_ARM_GOAL_TOLERANCE_RAD=.035

def validate_moveit_plan_for_direct_fjt(trajectory,target):
    names=list(trajectory.joint_names)
    if len(names)!=len(ARM) or set(names)!=set(ARM):
        raise ValueError("G04B_181_MOVEIT_TRAJECTORY_ARM_NAMES_INVALID")
    if set(target)!=set(ARM):
        raise ValueError("G04B_181_ARM_TARGET_INCOMPLETE")
    points=list(trajectory.points)
    if len(points)<2:
        raise ValueError("G04B_181_MOVEIT_TRAJECTORY_MISSING_POINTS")
    last_t=-1.0
    for point in points:
        pos=list(point.positions)
        if len(pos)!=len(names) or not all(math.isfinite(float(x)) for x in pos):
            raise ValueError("G04B_181_MOVEIT_TRAJECTORY_NONFINITE")
        t=float(point.time_from_start.sec)+float(point.time_from_start.nanosec)*1e-9
        if not math.isfinite(t) or t<=last_t:
            raise ValueError("G04B_181_MOVEIT_TRAJECTORY_TIME_NOT_INCREASING")
        last_t=t
    if last_t<=0:
        raise ValueError("G04B_181_MOVEIT_TRAJECTORY_NONPOSITIVE_DURATION")
    last=dict(zip(names,points[-1].positions))
    residual={n:abs(float(target[n])-float(last[n])) for n in ARM}
    if max(residual.values())>DIRECT_FJT_ARM_GOAL_TOLERANCE_RAD:
        raise ValueError("G04B_181_MOVEIT_PLAN_END_NOT_AT_GOAL")
    return {"joint_names":names,"planned_points":len(points),
            "duration_s":last_t,"planned_goal_residual_rad":residual}
