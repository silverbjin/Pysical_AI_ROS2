"""Ch07 Issue #181: independent arm FJT settlement acceptance; no physics fake."""
import math
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
JOINT_GOAL_TOL_RAD=.01
def assess_arm_settle(action_status,result_code,desired,measured):
    if action_status!=4 or result_code!=0:return ("ARM_SETTLE_ACTION_FAILED",{})
    if set(desired)!=set(ARM) or set(measured)!=set(ARM):return ("ARM_SETTLE_NAMES_INVALID",{})
    if not all(math.isfinite(float(desired[n])) and math.isfinite(float(measured[n])) for n in ARM):
        return ("ARM_SETTLE_NONFINITE",{})
    errors={n:abs(float(measured[n])-float(desired[n])) for n in ARM}
    return ("ARM_SETTLE_SCOPED_PASS" if max(errors.values())<=JOINT_GOAL_TOL_RAD
            else "ARM_SETTLE_ACTUAL_JOINTS_FAILED",errors)

# Issue #181 DART6.13 fixture run #43712237998: physical grasp/lift/hold/
# high transport PASS but MoveGroup lower_into_bin reports success with
# joint3 actual error 0.1348646 rad. Allow only a STRICT direct FJT
# completion of that one MoveGroup, with no relaxed final acceptance.
MOVEGROUP_FEEDBACK_MAX_ERROR_RAD=.075
LOWER_SETTLE_RECOVERY_MAX_INITIAL_ERROR_RAD=.18

def lower_bin_settle_recovery_eligible(label,errors):
    if label!="lower_into_bin" or not isinstance(errors,dict):
        return False
    if set(errors)!=set(ARM):return False
    if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0
               for v in errors.values()):return False
    worst=max(errors.values())
    return MOVEGROUP_FEEDBACK_MAX_ERROR_RAD<worst<=LOWER_SETTLE_RECOVERY_MAX_INITIAL_ERROR_RAD
