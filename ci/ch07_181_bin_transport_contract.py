"""Issue #181: position-only world-pose feedback for physically carried rod."""
import math
BIN_XY=(.55,.25)
LIFT_WRIST=(.48,0.,1.96)
LOWER_WRIST_Z=1.72
BIN_TOP_Z=1.73
ROD_HEIGHT=.08

def corrected_high_target(held_xyz):
    if len(held_xyz)!=3 or not all(math.isfinite(x) for x in held_xyz):
        raise ValueError("G04B_INVALID_HELD_WORLD_POSE")
    if held_xyz[2]<1.98:raise ValueError("G04B_ROD_NOT_HELD_HIGH")
    dx,dy=BIN_XY[0]-held_xyz[0],BIN_XY[1]-held_xyz[1]
    if math.hypot(dx,dy)>.35:raise ValueError("G04B_UNBOUNDED_TRANSFER")
    return [LIFT_WRIST[0]+dx,LIFT_WRIST[1]+dy,LIFT_WRIST[2]]

def custody_offset(rod,finger_center):
    if len(rod)!=3 or len(finger_center)!=3 or not all(
        math.isfinite(x) for x in (*rod,*finger_center)):
        raise ValueError("G04B_INVALID_CUSTODY_FEEDBACK")
    return tuple(rod[i]-finger_center[i] for i in range(3))

def custody_drift(rod,finger_center,held_offset):
    return math.dist(custody_offset(rod,finger_center),held_offset)

def high_arrival_valid(rod,drift):
    return (math.hypot(rod[0]-.55,rod[1]-.25)<=.07
            and rod[2]>=1.98 and math.isfinite(drift) and drift<=.04)

def feedback_centered_high_target(previous_wrist_target,actual_rod_world):
    """One bounded real MoveGroup correction derived from current GZ rod pose."""
    if (len(previous_wrist_target)!=3 or len(actual_rod_world)!=3 or
        not all(math.isfinite(float(x)) for x in
                (*previous_wrist_target,*actual_rod_world))):
        raise ValueError("G04B_181_HIGH_FEEDBACK_INVALID")
    if actual_rod_world[2]<1.98:
        raise ValueError("G04B_181_HIGH_ROD_NOT_HELD")
    dx=BIN_XY[0]-actual_rod_world[0]
    dy=BIN_XY[1]-actual_rod_world[1]
    if math.hypot(dx,dy)>.09:
        raise ValueError("G04B_181_HIGH_CORRECTION_TOO_LARGE")
    return [previous_wrist_target[0]+dx,
            previous_wrist_target[1]+dy,previous_wrist_target[2]]

def precise_high_arrival_valid(rod,drift):
    return (math.hypot(rod[0]-.55,rod[1]-.25)<=.025 and
            rod[2]>=1.98 and math.isfinite(drift) and drift<=.04)

def pre_release_valid(rod,recent_native_contact):
    """Fail closed using recent actual native Gazebo bilateral force, not
    the earlier invalid q2+q3+qwrist pseudo-FK metric. Physical final
    settled ROI/height, lift and hold gates remain independent.
    """
    if len(rod)!=3 or not all(math.isfinite(float(x)) for x in rod):
        return False
    return (math.hypot(rod[0]-.55,rod[1]-.25)<=.06
            and 1.78<=rod[2]<=1.92
            and isinstance(recent_native_contact,dict)
            and recent_native_contact.get("both_native_fresh_positive_force") is True
            and all(recent_native_contact.get("per_finger",{}).get(n,{}).get(
                "recent_contact_events",0)>=3 for n in ("finger1","finger2")))


# Historical 5DOF wrist command kept FOR CONTROLLED COMPARISON only:
# q2+q3+qwrist is not the world tool orientation when q4≈pi/2.
# Exact orientation is now measured with ch07_181_exact_fk; this helper
# does not prove real orientation preservation and must never mark PASS.
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
WRIST_LIMIT_RAD=1.5708

def finger_tilt(arm):
    if set(arm)!=set(ARM) or not all(math.isfinite(float(arm[n])) for n in ARM):
        raise ValueError("G04B_181_INVALID_REAL_ARM_JOINTSTATE")
    return float(arm["joint2"])+float(arm["joint3"])+float(arm["joint_wrist"])

def historical_wrist_bias_lower_goal(held_actual_arm,lower_nominal_arm):
    reference=finger_tilt(held_actual_arm)
    result={n:float(lower_nominal_arm[n]) for n in ARM}
    result["joint_wrist"]=reference-(result["joint2"]+result["joint3"])
    if abs(result["joint_wrist"])>WRIST_LIMIT_RAD:
        raise ValueError("G04B_181_WRIST_PITCH_COMPENSATION_LIMIT")
    if abs(finger_tilt(result)-reference)>1e-8:
        raise ValueError("G04B_181_HISTORICAL_WRIST_BIAS_CONSISTENCY")
    return result

def actual_finger_tilt_drift(held_arm,lower_arm):
    return abs(finger_tilt(lower_arm)-finger_tilt(held_arm))
