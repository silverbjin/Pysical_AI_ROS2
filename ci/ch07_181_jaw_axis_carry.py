"""Issue #181: original URDF jaw normal compensation for actual high transfer.

Robotic gripper physically held a 24mm cylinder while joint1 yaw changed
~0.4rad and joint4 remained pi/2, rotating the jaw separation normal in
world XYZ; raw #43683249305 lost 16.83cm object custody despite accurate
5DOF arm JointState. Compensate ONLY q4 to minimize the world jaw-axis
change during that same high waypoint, preserving wrist/rod target XYZ.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center, original_finger_tool_z_axis
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

# Cycle05: exact 5DOF WORLD jaw preserving lowered target. The historical
# q2+q3+qwrist angle-sum is not a valid WORLD orientation when q4~pi/2.
def exact_world_jaw_lower_plan(high_actual,lower_nominal,held_offset):
    if not all(isinstance(a,dict) and set(a)==set(ARM)
               for a in (high_actual,lower_nominal)):
        raise ValueError("G04B_181_LOWER_JAW_JOINTS_INCOMPLETE")
    if not isinstance(held_offset,(list,tuple)) or len(held_offset)!=3:
        raise ValueError("G04B_181_LOWER_JAW_HELD_OFFSET_MISSING")
    if not all(isinstance(x,(float,int)) and math.isfinite(x)
       for a in (high_actual,lower_nominal) for x in a.values()):
        raise ValueError("G04B_181_LOWER_JAW_NONFINITE")
    if not all(isinstance(x,(float,int)) and math.isfinite(x) for x in held_offset):
        raise ValueError("G04B_181_LOWER_JAW_OFFSET_NONFINITE")
    if math.dist(held_offset,(0.,0.,0.))>.055:
        raise ValueError("G04B_181_LOWER_JAW_OBJECT_NOT_IN_GRIPPER")
    x,y,z=real_jaw_world_axis(high_actual)
    yaw=lower_nominal["joint1"];theta=lower_nominal["joint2"]+lower_nominal["joint3"]
    # Rz(-yaw) Ry(-theta) world jaw, then inverse Rz(phi) Ry(wrist) ex.
    a=math.cos(yaw)*x+math.sin(yaw)*y
    b=-math.sin(yaw)*x+math.cos(yaw)*y
    ax=math.cos(theta)*a-math.sin(theta)*z
    az=math.sin(theta)*a+math.cos(theta)*z
    phi=math.atan2(b,ax)
    wrist=math.atan2(-az,math.hypot(ax,b))
    if not (-3.14159<=phi<=3.14159 and -1.5708<=wrist<=1.5708):
        raise ValueError("G04B_181_LOWER_JAW_LIMIT")
    goal=dict(lower_nominal,joint4=phi,joint_wrist=wrist)
    old=dict(lower_nominal)
    old["joint_wrist"]=(high_actual["joint2"]+high_actual["joint3"]+
                        high_actual["joint_wrist"]-
                        lower_nominal["joint2"]-lower_nominal["joint3"])
    old_change=real_jaw_world_axis_change(high_actual,old)
    change=real_jaw_world_axis_change(high_actual,goal)
    if change>1e-5 or old_change-change<.10:
        raise ValueError("G04B_181_EXACT_LOWER_JAW_NO_IMPROVEMENT")
    def tool_angle(target):
        a=original_finger_tool_z_axis(high_actual)
        b=original_finger_tool_z_axis(target)
        return math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(a,b)))))
    new_tool=tool_angle(goal); old_tool=tool_angle(old)
    if new_tool>.38 or new_tool>old_tool:
        raise ValueError("G04B_181_EXACT_LOWER_TOOL_DIRECTION_UNSAFE")
    c=original_finger_collision_center(goal)
    rod=[c[i]+held_offset[i] for i in range(3)]
    xy=math.hypot(rod[0]-.55,rod[1]-.25)
    if xy>.06 or not (1.78<=rod[2]<=1.92):
        raise ValueError("G04B_181_EXACT_LOWER_ROD_OUTSIDE_BIN")
    return {"target":goal,"predicted_rod_xyz_m":rod,
            "predicted_bin_xy_error_m":xy,"jaw_world_change_rad":change,
            "historical_jaw_world_change_rad":old_change,
            "tool_world_change_rad":new_tool,
            "historical_tool_world_change_rad":old_tool,
            "scope":"KINEMATIC_ONLY_NOT_PHYSICAL_PASS"}
