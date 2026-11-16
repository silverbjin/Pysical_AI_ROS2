"""G04B Cycle06: collision-safe lower release with q3 below native stall.

Single change from Cycle05: lower waypoint geometry (NOT tolerance or
physics). Original 5DOF kinematics/world jaw pose preserved; native rod
placement is still independently tested.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center,actual_tool_axis_angle_rad
from ch07_181_jaw_axis_carry import real_jaw_world_axis,real_jaw_world_axis_change
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
SAFE_Q3_RAD=1.05
STALLED_Q3_RAD=1.132
BIN_RELEASE_ROD=(.55,.25,1.90)

def reachable_release_waypoint(high,lower,offset):
    if not all(isinstance(a,dict) and set(a)==set(ARM) for a in (high,lower)):
        raise ValueError("CYCLE06_JOINT_NAMES_INVALID")
    if not isinstance(offset,(list,tuple)) or len(offset)!=3:
        raise ValueError("CYCLE06_HELD_OFFSET_INVALID")
    if any(not isinstance(x,(float,int)) or not math.isfinite(float(x))
           for a in (high,lower) for x in a.values()):
        raise ValueError("CYCLE06_NONFINITE_JOINT")
    if any(not isinstance(x,(float,int)) or not math.isfinite(float(x)) for x in offset):
        raise ValueError("CYCLE06_NONFINITE_OFFSET")
    if math.dist(offset,(0.,0.,0.))>.055 or lower["joint3"]-SAFE_Q3_RAD<.12:
        raise ValueError("CYCLE06_HELD_OR_JOINT_AVOIDANCE_INVALID")
    direction=real_jaw_world_axis(high)
    def sample(yaw,q2):
        theta=q2+SAFE_Q3_RAD
        x,y,z=direction
        a=math.cos(yaw)*x+math.sin(yaw)*y
        b=-math.sin(yaw)*x+math.cos(yaw)*y
        lx=math.cos(theta)*a-math.sin(theta)*z
        lz=math.sin(theta)*a+math.cos(theta)*z
        q={"joint1":yaw,"joint2":q2,"joint3":SAFE_Q3_RAD,
           "joint4":math.atan2(b,lx),
           "joint_wrist":math.atan2(-lz,math.hypot(lx,b))}
        f=original_finger_collision_center(q)
        return q,[f[i]+offset[i] for i in range(3)]
    # Deterministic bounded least squares in two variables, pure stdlib:
    # no Goal/physics execution and no scipy dependency.
    yaw,q2=float(lower["joint1"]),-.29
    for _ in range(16):
        _,p=sample(yaw,q2)
        e=[p[i]-BIN_RELEASE_ROD[i] for i in range(3)]
        h=1e-5
        _,px=sample(yaw+h,q2)
        _,py=sample(yaw,q2+h)
        a=[(px[i]-p[i])/h for i in range(3)]
        b=[(py[i]-p[i])/h for i in range(3)]
        aa=sum(x*x for x in a)+1e-5
        ab=sum(a[i]*b[i] for i in range(3))
        bb=sum(x*x for x in b)+1e-5
        ac=sum(a[i]*e[i] for i in range(3))
        bc=sum(b[i]*e[i] for i in range(3))
        den=aa*bb-ab*ab
        if not math.isfinite(den) or den<=1e-8:
            raise ValueError("CYCLE06_JACOBIAN_SINGULAR")
        dy=(bb*ac-ab*bc)/den
        d2=(aa*bc-ab*ac)/den
        yaw-=max(-.08,min(.08,dy))
        q2-=max(-.08,min(.08,d2))
        if abs(yaw-lower["joint1"])>.12 or not -.55<=q2<=-.10:
            raise ValueError("CYCLE06_OUTSIDE_BOUNDED_SEARCH")
    goal,rod=sample(yaw,q2)
    xy=math.hypot(rod[0]-.55,rod[1]-.25)
    jaw=real_jaw_world_axis_change(high,goal)
    tool=actual_tool_axis_angle_rad(high,goal)
    if xy>.015 or not 1.87<=rod[2]<=1.92:
        raise ValueError("CYCLE06_ROD_OUTSIDE_BIN_RELEASE_ENVELOPE")
    if (jaw>1e-5 or tool>.38 or
        abs(goal["joint1"])>3.14159 or
        abs(goal["joint2"])>1.57079 or
        abs(goal["joint3"])>2.0944 or
        abs(goal["joint4"])>3.14159 or
        abs(goal["joint_wrist"])>1.5708):
        raise ValueError("CYCLE06_JOINT_OR_TOOL_UNSAFE")
    if SAFE_Q3_RAD>STALLED_Q3_RAD-.07:
        raise ValueError("CYCLE06_TOO_CLOSE_TO_NATIVE_STALL")
    return {"target":goal,"predicted_rod_world_xyz_m":rod,
            "predicted_bin_xy_error_m":xy,
            "predicted_release_drop_m":rod[2]-(1.73+.08/2),
            "world_jaw_change_rad":jaw,"world_tool_change_rad":tool,
            "single_factor":"REACHABLE_LOWER_RELEASE_WAYPOINT",
            "scope":"KINEMATIC_ONLY_NOT_PHYSICAL_ACCEPTANCE"}
