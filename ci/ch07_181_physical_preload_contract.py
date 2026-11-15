"""Ch07 Issue #181: real bilateral 2mm prismatic lower-stop release.

Observed CI #43599142218: finger2 prepositioned 2mm -> actual 11mm,
but finger1 left at 0mm -> stuck despite FJT reference 11mm.
Never treat JTC reference/Action alone as proof of the actual position.
"""
import math
FINGERS=("joint_finger1","joint_finger2")
EXPECTED_PRELOAD_M=.002
PRELOAD_MAX_ERROR_M=.0005

def actual_preload_pass(record,after_arm,preclose):
    if not isinstance(record,dict):return False
    if record.get("name")!="lower_stop_release_both_fingers_2mm":return False
    if record.get("status")!=4 or record.get("result_error")!=0:return False
    if record.get("joint_tracking_pass") is not True:return False
    desired=record.get("command_by_joint_m")
    initial=record.get("actual_m")
    if not all(isinstance(x,dict) and set(x)==set(FINGERS) for x in
               (desired,initial,after_arm,preclose)):
        return False
    if not all(math.isfinite(float(v)) for x in
               (desired,initial,after_arm,preclose) for v in x.values()
               if isinstance(v,(float,int))):
        return False
    if not all(isinstance(v,(float,int)) and math.isfinite(v)
               for x in (desired,initial,after_arm,preclose) for v in x.values()):
        return False
    if any(desired[n]!=EXPECTED_PRELOAD_M for n in FINGERS):return False
    return all(abs(x[n]-EXPECTED_PRELOAD_M)<=PRELOAD_MAX_ERROR_M
               for x in (initial,after_arm,preclose) for n in FINGERS)


def isolated_finger1_release_pass(record):
    """One isolated physical FJT step, before the unchanged bilateral 2mm gate.

    A negative result MUST stop immediately; do not send a second Goal if
    finger1 remains stuck at q0. This tests single-joint sequencing, not a
    change to source geometry, SDF limits, controller gains or tolerances.
    """
    if not isinstance(record,dict):return False
    if record.get("name")!="lower_stop_release_finger1_only_2mm":return False
    if record.get("status")!=4 or record.get("result_error")!=0:return False
    if record.get("joint_tracking_pass") is not True:return False
    desired=record.get("command_by_joint_m")
    actual=record.get("actual_m")
    if not all(isinstance(q,dict) and set(q)==set(FINGERS) for q in (desired,actual)):
        return False
    expected={"joint_finger1":EXPECTED_PRELOAD_M,"joint_finger2":0.}
    if any(not isinstance(actual[n],(float,int)) or not math.isfinite(actual[n])
           for n in FINGERS):return False
    if desired!=expected:return False
    return all(abs(actual[n]-expected[n])<=PRELOAD_MAX_ERROR_M for n in FINGERS)
