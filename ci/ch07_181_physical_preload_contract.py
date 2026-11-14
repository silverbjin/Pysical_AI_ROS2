"""Issue #181: physical 2mm lower-limit release must use real FJT and JointState."""
import math
EXPECTED_PRELOAD_M=.002
PRELOAD_MAX_ERROR_M=.0005
def actual_preload_pass(record,after_arm_m,preclose_m):
    if not isinstance(record,dict):return False
    values=record.get("command_by_joint_m") or {}
    actual=record.get("actual_m") or {}
    if record.get("name")!="lower_stop_release_finger2_2mm":return False
    if record.get("status")!=4 or record.get("result_error")!=0:return False
    if not record.get("joint_tracking_pass"):return False
    if values.get("joint_finger2")!=EXPECTED_PRELOAD_M:return False
    if values.get("joint_finger1")!=0:return False
    if any(not isinstance(v,(int,float)) or not math.isfinite(v)
           for v in [actual.get("joint_finger2"),after_arm_m,preclose_m]):
        return False
    return all(abs(v-EXPECTED_PRELOAD_M)<=PRELOAD_MAX_ERROR_M
               for v in [actual["joint_finger2"],after_arm_m,preclose_m])
