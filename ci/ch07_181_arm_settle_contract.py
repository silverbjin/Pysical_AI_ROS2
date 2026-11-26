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
