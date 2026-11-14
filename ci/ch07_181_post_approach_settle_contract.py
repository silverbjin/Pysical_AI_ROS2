#!/usr/bin/env python3
"""Issue #181: final contact alignment arm-settle target must be measured, not fabricated."""
import math
ARM=("joint1","joint2","joint3","joint4","joint_wrist")

def measured_contact_settle_target(actual):
    if set(actual)!=set(ARM) or not all(math.isfinite(float(actual[n])) for n in ARM):
        raise ValueError("G04B_181_CONTACT_SETTLE_JOINTSTATE_INVALID")
    if abs(float(actual["joint4"])-math.pi/2)>.005 or abs(float(actual["joint_wrist"]))>.005:
        raise ValueError("G04B_181_CONTACT_SETTLE_AXES_NOT_ALIGNED")
    return {n:float(actual[n]) for n in ARM}

def unchanged_collision_center(previous_xyz,after_xyz,max_motion_m=.004):
    if len(previous_xyz)!=3 or len(after_xyz)!=3 or not all(math.isfinite(float(x)) for x in (*previous_xyz,*after_xyz)):
        return False
    return math.dist(previous_xyz,after_xyz)<=max_motion_m
