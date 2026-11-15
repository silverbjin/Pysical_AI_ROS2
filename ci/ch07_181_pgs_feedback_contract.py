"""Issue #181: one PGS-only guarded WORLD feedback correction.

Original single-factor DART PGS CI #43690734272 carried the native cylinder
to real [0.537241,0.215016,2.07376] vs bin [0.55,0.25], with original true
FK geometric custody drift 0.03704m (< strict 0.04m). It failed only the
existing strict precise high-bin XY<=0.025m. Never retry if custody lost or
original high error>40mm as in earlier Dantzig raw RED runs.
"""
import math
from ch07_181_bin_transport_contract import (
    feedback_centered_high_target,precise_high_arrival_valid)
BIN_XY=(.55,.25)
MAX_DELTA_M=.04
MAX_CUSTODY_M=.04
MAX_Q4_DRIFT_RAD=.005
MAX_REAL_JOINT_ERROR_RAD=.01

def pgs_bounded_recenter(old_high_target,rod_world,real_custody_drift_m,
                         actual_arm):
    if len(rod_world)!=3 or len(old_high_target)!=3:
        raise ValueError("G04B_181_PGS_MISSING_WORLD_POSE")
    if not all(isinstance(x,(float,int)) and math.isfinite(x)
            for x in (*rod_world,*old_high_target,real_custody_drift_m)):
        raise ValueError("G04B_181_PGS_NONFINITE")
    if real_custody_drift_m>MAX_CUSTODY_M or real_custody_drift_m<0:
        raise ValueError("G04B_181_PGS_ACTUAL_GRASP_CUSTODY_NOT_PROVEN")
    dist=math.hypot(rod_world[0]-.55,rod_world[1]-.25)
    if dist>MAX_DELTA_M or rod_world[2]<1.98:
        raise ValueError("G04B_181_PGS_FEEDBACK_CORRECTION_OUT_OF_BOUNDS")
    if set(actual_arm)!=set(("joint1","joint2","joint3","joint4","joint_wrist")):
        raise ValueError("G04B_181_PGS_MISSING_ACTUAL_Q")
    if not all(math.isfinite(float(x)) for x in actual_arm.values()):
        raise ValueError("G04B_181_PGS_NONFINITE_ACTUAL_Q")
    return {"candidate_wrist_xyz_m":
            feedback_centered_high_target(old_high_target,rod_world),
            "real_rod_xy_error_before_m":dist,
            "real_geometric_custody_before_m":real_custody_drift_m,
            "held_q4_rad":float(actual_arm["joint4"]),
            "held_qwrist_rad":float(actual_arm["joint_wrist"]),
            "permitted_correction_m":MAX_DELTA_M,
            "candidate_goal_count":1,
            "PGS_PHYSICS_ONLY":True}

def verify_post_correction(real_rod_world,real_custody_drift_m,
                           goal_joint_positions,actual_joint_positions):
    if set(goal_joint_positions)!=set(actual_joint_positions):
        return {"physical_fine_high_PASS":False,"cause":"JOINT_SET_INCOMPLETE"}
    if not all(math.isfinite(float(x)) for x in
        (*real_rod_world,real_custody_drift_m,*goal_joint_positions.values(),
         *actual_joint_positions.values())):
        return {"physical_fine_high_PASS":False,"cause":"NONFINITE"}
    if abs(actual_joint_positions["joint4"]-
           goal_joint_positions["joint4"])>MAX_Q4_DRIFT_RAD:
        return {"physical_fine_high_PASS":False,"cause":"JAW_Q4_DRIFT"}
    err=max(abs(actual_joint_positions[n]-goal_joint_positions[n])
            for n in goal_joint_positions)
    return {"physical_fine_high_PASS":bool(
        err<=MAX_REAL_JOINT_ERROR_RAD and
        precise_high_arrival_valid(real_rod_world,real_custody_drift_m)),
        "max_actual_joint_error_rad":err,
        "real_bin_xy_error_m":math.hypot(real_rod_world[0]-.55,
                                        real_rod_world[1]-.25),
        "real_custody_drift_m":real_custody_drift_m,
        "cause":"PHYSICS_AND_GEOMETRY_STRICT_NOT_MET"}
