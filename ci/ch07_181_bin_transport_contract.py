"""Issue #181: position-only world-pose feedback for physically carried rod."""
import math
from ch07_181_exact_fk import original_finger_collision_center
BIN_XY=(.55,.25)
LIFT_WRIST=(.48,0.,1.96)
LOWER_WRIST_Z=1.72
BIN_TOP_Z=1.73
ROD_HEIGHT=.08

def inverse_original_2r_high_wrist(wrist_xyz):
    """Original 2R position IK, q4=pi/2 and qwrist=0 used for high carry."""
    x,y,z=map(float,wrist_xyz)
    r=math.hypot(x,y);dz=z-.6
    c=(r*r+dz*dz-.5*.5-1.)/(2*.5*1.)
    if not math.isfinite(c) or abs(c)>1:
        raise ValueError("G04B_181_HIGH_ARM_UNREACHABLE")
    q3=math.acos(c)
    q2=math.atan2(r,dz)-math.atan2(math.sin(q3),.5+math.cos(q3))
    q={"joint1":math.atan2(y,x),"joint2":q2,"joint3":q3,
       "joint4":math.pi/2,"joint_wrist":0.}
    if abs(q2)>1.57079 or abs(q3)>2.0944:
        raise ValueError("G04B_181_HIGH_JOINT_LIMIT")
    return q

def exact_fk_high_bin_wrist_target(held_actual_arm,held_rod_world):
    """Solve actual gripper+rod position rather than use frozen lift wrist.

    The prior target wrist=(.48,0,1.96)+(bin-current rod XY) ignored
    the entire 100mm wrist-to-finger collision-centre tool offset.
    Use a measured held-world rod offset and 4 deterministic inverse-FK
    iterations (pure computation, not repeated robot motions).
    """
    if len(held_rod_world)!=3 or not all(
           math.isfinite(float(v)) for v in held_rod_world):
        raise ValueError("G04B_181_HELD_ROD_INVALID")
    held_fk=original_finger_collision_center(held_actual_arm)
    offset=[held_rod_world[i]-held_fk[i] for i in range(3)]
    if math.dist(held_rod_world,held_fk)>.055:
        raise ValueError("G04B_181_HELD_ROD_NOT_IN_REAL_FINGERS")
    wrist=[BIN_XY[0]-offset[0],BIN_XY[1]-offset[1],LIFT_WRIST[2]]
    for _ in range(5):
        pred=original_finger_collision_center(
            inverse_original_2r_high_wrist(wrist))
        predicted=[pred[i]+offset[i] for i in range(3)]
        wrist[0]+=BIN_XY[0]-predicted[0]
        wrist[1]+=BIN_XY[1]-predicted[1]
    if math.hypot(wrist[0]-LIFT_WRIST[0],
                  wrist[1]-LIFT_WRIST[1])>.35:
        raise ValueError("G04B_181_UNBOUNDED_WRT_LIFT_TARGET")
    predicted=original_finger_collision_center(
        inverse_original_2r_high_wrist(wrist))
    if math.hypot(predicted[0]+offset[0]-BIN_XY[0],
                  predicted[1]+offset[1]-BIN_XY[1])>.001:
        raise ValueError("G04B_181_HIGH_WRT_FK_NOT_CONVERGED")
    return wrist

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

def pre_release_valid(rod,geometric_drift_m,recent_native_contact):
    """Fail closed using recent actual native Gazebo bilateral force, not
    the earlier invalid q2+q3+qwrist pseudo-FK metric. Physical final
    settled ROI/height, lift and hold gates remain independent.
    """
    if len(rod)!=3 or not all(math.isfinite(float(x)) for x in rod):
        return False
    return (math.hypot(rod[0]-.55,rod[1]-.25)<=.06
            and 1.78<=rod[2]<=1.92
            # Even when Gazebo contact topic continues to publish, raw
            # #43604397028 showed a 0.213m object-vs-finger separation.
            # A fresh contact alone CANNOT replace true original FK custody.
            and isinstance(geometric_drift_m,(int,float))
            and math.isfinite(geometric_drift_m)
            and geometric_drift_m<=.04
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
