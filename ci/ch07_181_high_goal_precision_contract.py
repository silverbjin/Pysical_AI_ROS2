"""Issue #181: strict *actual* joint arrival at first high physical transport.

Raw public CI #43605465669: MoveGroup SUCCEEDED at 35mrad tolerance
even though arm joints missed goal by ~34mrad, causing 51.45mm
real cylinder XY bin miss. Do not issue a second unbounded XY move.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
HIGH_MOVEGROUP_JOINT_CONSTRAINT_RAD=.002
HIGH_ACTUAL_JOINT_MAX_ERROR_RAD=.01
HIGH_FK_BIN_TARGET_MAX_ERROR_M=.005
BIN_XY=(.55,.25)
def assess_precise_high_arrival(goal,actual,held_object_offset):
    if not all(isinstance(x,dict) and set(x)==set(ARM) for x in (goal,actual)):
        raise ValueError("G04B_181_HIGH_ARM_JOINTSTATE_INCOMPLETE")
    if len(held_object_offset)!=3:
        raise ValueError("G04B_181_HELD_OFFSET_INCOMPLETE")
    if not all(isinstance(v,(float,int)) and math.isfinite(float(v))
        for x in (goal,actual) for v in x.values()):
        raise ValueError("G04B_181_HIGH_ARM_JOINTSTATE_NONFINITE")
    if not all(math.isfinite(float(v)) for v in held_object_offset):
        raise ValueError("G04B_181_HELD_OFFSET_NONFINITE")
    err={n:abs(float(goal[n])-float(actual[n])) for n in ARM}
    center=original_finger_collision_center(actual)
    ideal_center=original_finger_collision_center(goal)
    actual_estimated_rod=[center[i]+held_object_offset[i] for i in range(3)]
    ideal_estimated_rod=[ideal_center[i]+held_object_offset[i] for i in range(3)]
    expected_err=math.hypot(ideal_estimated_rod[0]-BIN_XY[0],
                            ideal_estimated_rod[1]-BIN_XY[1])
    return {"per_joint_error_rad":err,
            "max_joint_error_rad":max(err.values()),
            "ideal_object_bin_xy_error_m":expected_err,
            "actual_jointstate_predicted_rod_xyz_m":actual_estimated_rod,
            "real_arm_tracking_scoped_pass":(
               max(err.values())<=HIGH_ACTUAL_JOINT_MAX_ERROR_RAD
               and expected_err<=HIGH_FK_BIN_TARGET_MAX_ERROR_M)}
