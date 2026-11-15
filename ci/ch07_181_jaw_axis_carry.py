"""Issue #181: original URDF jaw normal compensation for actual high transfer.

Robotic gripper physically held a 24mm cylinder while joint1 yaw changed
~0.4rad and joint4 remained pi/2, rotating the jaw separation normal in
world XYZ; raw #43683249305 lost 16.83cm object custody despite accurate
5DOF arm JointState. Compensate ONLY q4 to minimize the world jaw-axis
change during that same high waypoint, preserving wrist/rod target XYZ.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
MAX_Q4_DEVIATION_FROM_PREVIOUS_NOMINAL_RAD=.5
MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD=.25
MIN_EXPECTED_JAW_NORMAL_IMPROVEMENT_RAD=.10

def real_jaw_world_axis(arm):
    if not isinstance(arm,dict) or set(arm)!=set(ARM):
        raise ValueError("G04B_181_JAW_ACTUAL_ARM_STATE_MISSING")
    if any(not isinstance(x,(float,int)) or not math.isfinite(float(x))
           for x in arm.values()):
        raise ValueError("G04B_181_JAW_NONFINITE")
    yaw=float(arm["joint1"]);theta=float(arm["joint2"])+float(arm["joint3"])
    phi=float(arm["joint4"]);w=float(arm["joint_wrist"])
    # Rz(yaw) Ry(theta) Rz(phi) Ry(wrist) e_x.
    ux=math.cos(theta)*math.cos(phi)*math.cos(w)-math.sin(theta)*math.sin(w)
    uy=math.sin(phi)*math.cos(w)
    uz=-math.sin(theta)*math.cos(phi)*math.cos(w)-math.cos(theta)*math.sin(w)
    return [ux*math.cos(yaw)-uy*math.sin(yaw),
            ux*math.sin(yaw)+uy*math.cos(yaw),uz]

def real_jaw_world_axis_change(a,b):
    x=real_jaw_world_axis(a);y=real_jaw_world_axis(b)
    dot=max(-1.0,min(1.0,sum(i*j for i,j in zip(x,y))))
    return math.acos(dot)

def high_carry_jaw_compensation(held_actual_arm,nominal_high_goal):
    reference=real_jaw_world_axis(held_actual_arm)
    target=dict(nominal_high_goal)
    _=real_jaw_world_axis(target)
    if abs(target["joint_wrist"])>1e-8:
        raise ValueError("G04B_181_NONZERO_HIGH_WRIST_OUT_OF_SCOPE")
    a=real_jaw_world_axis({**target,"joint4":0.0})
    b=real_jaw_world_axis({**target,"joint4":math.pi/2})
    coscoef=sum(u*v for u,v in zip(reference,a))
    sincoef=sum(u*v for u,v in zip(reference,b))
    q4=math.atan2(sincoef,coscoef)
    if abs(q4-target["joint4"])>MAX_Q4_DEVIATION_FROM_PREVIOUS_NOMINAL_RAD:
        raise ValueError("G04B_181_JAW_Q4_UNBOUNDED_COMPENSATION")
    target["joint4"]=q4
    oldchange=real_jaw_world_axis_change(held_actual_arm,nominal_high_goal)
    newchange=real_jaw_world_axis_change(held_actual_arm,target)
    if oldchange-newchange<MIN_EXPECTED_JAW_NORMAL_IMPROVEMENT_RAD:
        raise ValueError("G04B_181_JAW_COMPENSATION_NO_MEASURABLE_BENEFIT")
    if newchange>MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD:
        raise ValueError("G04B_181_JAW_TARGET_DRIFT_EXCESS")
    previous_xyz=original_finger_collision_center(nominal_high_goal)
    compensated_xyz=original_finger_collision_center(target)
    if math.dist(previous_xyz,compensated_xyz)>1e-8:
        raise ValueError("G04B_181_JAW_CHANGED_OBJECT_TRANSPORT_POSITION")
    return {"target":target,"original_predicted_jaw_change_rad":oldchange,
            "compensated_predicted_jaw_change_rad":newchange,
            "jaw_axis_world_reference":reference,
            "jaw_axis_world_target":real_jaw_world_axis(target),
            "physical_rod_position_target_unchanged":True}
