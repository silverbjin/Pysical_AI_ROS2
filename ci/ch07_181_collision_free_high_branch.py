"""Cycle09: alternate 2R elbow branch while retaining exact carried-rod XY.

Only high target joint configuration changes; actual MoveIt scene must
independently certify goal/trajectory collision free BEFORE real motion.
No ROS, Gazebo or physical-object commands in this module.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center
from ch07_181_jaw_axis_carry import high_carry_jaw_compensation,real_jaw_world_axis_change

def alternative_high_elbow_target(held_actual,held_rod,original_wrist):
    if not isinstance(held_actual,dict) or len(held_rod)!=3 or len(original_wrist)!=3:
        raise ValueError("C09_INPUT_INVALID")
    if not all(math.isfinite(float(x)) for x in (*held_rod,*original_wrist)):
        raise ValueError("C09_NONFINITE")
    held_center=original_finger_collision_center(held_actual)
    offset=[held_rod[i]-held_center[i] for i in range(3)]
    if math.dist(offset,(0.,0.,0.))>.055:
        raise ValueError("C09_HELD_ROD_NOT_IN_GRIPPER")
    wrist=list(original_wrist)
    for _ in range(8):
        x,y,z=wrist
        radius=math.hypot(x,y);dz=z-.6
        c=(radius*radius+dz*dz-1.25)/(1.0)
        if not -1<=c<=1:raise ValueError("C09_ELBOW_ALT_UNREACHABLE")
        q3=-math.acos(c)
        q2=math.atan2(radius,dz)-math.atan2(math.sin(q3),.5+math.cos(q3))
        q={"joint1":math.atan2(y,x),"joint2":q2,"joint3":q3,
           "joint4":math.pi/2,"joint_wrist":0.}
        predicted=original_finger_collision_center(q)
        rod=[predicted[i]+offset[i] for i in range(3)]
        wrist[0]+=.55-rod[0]
        wrist[1]+=.25-rod[1]
    if not (.0<q["joint2"]<1.57079 and -2.0944<=q3<-.10):
        raise ValueError("C09_NEGATIVE_ELBOW_BRANCH_INVALID")
    plan=high_carry_jaw_compensation(held_actual,q)
    goal=plan["target"]
    rod=[original_finger_collision_center(goal)[i]+offset[i] for i in range(3)]
    xy=math.hypot(rod[0]-.55,rod[1]-.25)
    if xy>.003 or rod[2]<1.98 or real_jaw_world_axis_change(held_actual,goal)>.25:
        raise ValueError("C09_PREDICTED_CUSTODY_OR_BIN_INVALID")
    return {"joint_goal":goal,"predicted_rod_xyz_m":rod,
            "predicted_bin_xy_error_m":xy,
            "high_wrist_xyz_m":wrist,"elbow_branch":"NEGATIVE",
            "requires_moveit_plan_only_before_real_goal":True,
            "G04B":"BLOCKED_UNTIL_NATIVE_PHYSICAL_ACCEPTANCE"}
