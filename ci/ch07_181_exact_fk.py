"""Exact original Ch07 5DOF manipulator collision-centre kinematics.

Original URDF chain (verified from #43600241307 raw robot.urdf):
Rz(joint1) Ry(joint2+joint3) Rz(joint4) Ry(joint_wrist).
For joint4≈pi/2 the wrist rotation axis is NOT the same as arm pitch.
No artificial model/physics change; pure read-only position estimation.
"""
import math
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
FINGER_COLLISION_CENTRE_LOCAL_Z_M=.10

def original_finger_collision_center(arm):
    if set(arm)!=set(ARM) or any(not math.isfinite(float(arm[n])) for n in ARM):
        raise ValueError("G04B_181_INVALID_ACTUAL_ARM_JOINTSTATE")
    yaw,theta,q4,qw=(float(arm["joint1"]),float(arm["joint2"])+float(arm["joint3"]),
                     float(arm["joint4"]),float(arm["joint_wrist"]))
    r=.5*math.sin(arm["joint2"])+math.sin(theta)
    z=.6+.5*math.cos(arm["joint2"])+math.cos(theta)
    # tool local +Z: Ry(theta) Rz(q4) Ry(qw) e_z
    ux=math.cos(theta)*math.cos(q4)*math.sin(qw)+math.sin(theta)*math.cos(qw)
    uy=math.sin(q4)*math.sin(qw)
    uz=-math.sin(theta)*math.cos(q4)*math.sin(qw)+math.cos(theta)*math.cos(qw)
    d=FINGER_COLLISION_CENTRE_LOCAL_Z_M
    return [r*math.cos(yaw)+d*(ux*math.cos(yaw)-uy*math.sin(yaw)),
            r*math.sin(yaw)+d*(ux*math.sin(yaw)+uy*math.cos(yaw)),
            z+d*uz]

def original_finger_tool_z_axis(arm):
    if set(arm)!=set(ARM) or any(not math.isfinite(float(arm[n])) for n in ARM):
        raise ValueError("G04B_181_INVALID_ACTUAL_ARM_JOINTSTATE")
    yaw=float(arm["joint1"])
    theta=float(arm["joint2"])+float(arm["joint3"])
    q4=float(arm["joint4"])
    qw=float(arm["joint_wrist"])
    ux=math.cos(theta)*math.cos(q4)*math.sin(qw)+math.sin(theta)*math.cos(qw)
    uy=math.sin(q4)*math.sin(qw)
    uz=-math.sin(theta)*math.cos(q4)*math.sin(qw)+math.cos(theta)*math.cos(qw)
    return [ux*math.cos(yaw)-uy*math.sin(yaw),
            ux*math.sin(yaw)+uy*math.cos(yaw),uz]

def actual_tool_axis_angle_rad(first_arm,last_arm):
    first=original_finger_tool_z_axis(first_arm)
    last=original_finger_tool_z_axis(last_arm)
    dot=max(-1.,min(1.,sum(a*b for a,b in zip(first,last))))
    return math.acos(dot)
