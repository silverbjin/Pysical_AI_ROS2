"""Cycle10 original-bin 3D link4 box SAT high-goal selector; offline only.

Ch07 source: world-fixed test robot base (0,0,0); link4 0.05x0.05x0.5m,
original static bin 0.30x0.30x0.20m at (0.55,0.25,1.63).
Never substitute this kinematic filter for MoveIt FCL or native physics.
"""
import math
from ch07_181_exact_fk import original_finger_collision_center
from ch07_181_high_goal_precision_contract import HIGH_FK_BIN_TARGET_MAX_ERROR_M
from ch07_181_jaw_axis_carry import (
    high_carry_jaw_compensation, real_jaw_world_axis_change)

ARM=("joint1","joint2","joint3","joint4","joint_wrist")
BIN=(.55,.25,1.63)
BIN_HALF=(.15,.15,.10)
LINK4_HALF=(.025,.025,.25)

def dot(a,b):
    return sum(x*y for x,y in zip(a,b))

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def valid_arm(q):
    return (isinstance(q,dict) and set(q)==set(ARM) and
            all(isinstance(v,(float,int)) and math.isfinite(v)
                for v in q.values()))

def original_link4_bin_sat_margin(q):
    """Positive means a 3D box separating axis exists, not a path."""
    if not valid_arm(q):
        raise ValueError("C10_INVALID_ARM")
    yaw=q["joint1"];q2=q["joint2"];theta=q2+q["joint3"]
    phi=q["joint4"]
    cy,sy=math.cos(yaw),math.sin(yaw)
    ct,st=math.cos(theta),math.sin(theta)
    cp,sp=math.cos(phi),math.sin(phi)
    axes=((cy*ct*cp-sy*sp,sy*ct*cp+cy*sp,-st*cp),
          (-cy*ct*sp-sy*cp,-sy*ct*sp+cy*cp,st*sp),
          (cy*st,sy*st,ct))
    radial=.5*math.sin(q2)+.75*math.sin(theta)
    center=(radial*cy,radial*sy,.6+.5*math.cos(q2)+.75*math.cos(theta))
    delta=tuple(BIN[k]-center[k] for k in range(3))
    world=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    separating_axes=list(axes)+list(world)
    for a in axes:
        for b in world:
            v=cross(a,b)
            norm=math.sqrt(dot(v,v))
            if norm>1e-10:
                separating_axes.append(tuple(x/norm for x in v))
    margin=-float("inf")
    for u in separating_axes:
        projected=sum(LINK4_HALF[k]*abs(dot(axes[k],u))
                      for k in range(3))
        projected+=sum(BIN_HALF[k]*abs(u[k]) for k in range(3))
        margin=max(margin,abs(dot(delta,u))-projected)
    return margin

def source_bin_clearance_high_goal(held_arm,held_rod,scene):
    if not valid_arm(held_arm):
        raise ValueError("C10_HELD_ARM_INVALID")
    if (not isinstance(held_rod,(list,tuple)) or len(held_rod)!=3 or
        any(not isinstance(v,(float,int)) or not math.isfinite(v)
            for v in held_rod)):
        raise ValueError("C10_HELD_ROD_INVALID")
    if (not isinstance(scene,dict) or
        scene.get("apply_planning_scene_success") is not True or
        scene.get("id")!="g04b_existing_gazebo_bin_collision" or
        scene.get("frame_id")!="base_link" or
        tuple(scene.get("center_m",()))!=BIN or
        tuple(scene.get("box_m",()))!=(.30,.30,.20)):
        raise ValueError("C10_ORIGINAL_BIN_SCENE_NOT_PROVEN")
    center=original_finger_collision_center(held_arm)
    offset=tuple(held_rod[k]-center[k] for k in range(3))
    if math.sqrt(dot(offset,offset))>.055:
        raise ValueError("C10_ROD_NOT_HELD")
    yaw=math.atan2(.25-offset[1],.55-offset[0])
    best=None
    trials=0
    for i in range(-15,16):
        for j in range(112,177):
            nominal=dict(zip(ARM,(yaw,i*.004,j*.004,math.pi/2,0.)))
            try:
                q=high_carry_jaw_compensation(held_arm,nominal)["target"]
            except ValueError:
                continue
            trials+=1
            f=original_finger_collision_center(q)
            rod=tuple(f[k]+offset[k] for k in range(3))
            xy=math.hypot(rod[0]-.55,rod[1]-.25)
            jaw=real_jaw_world_axis_change(held_arm,q)
            margin=original_link4_bin_sat_margin(q)
            if xy>HIGH_FK_BIN_TARGET_MAX_ERROR_M or rod[2]<1.98 or jaw>.25 or margin<.003:
                continue
            # Balance both metre-valued margins and radian jaw reserve.
            score=min(margin-.003,HIGH_FK_BIN_TARGET_MAX_ERROR_M-xy,
                      .1*(.25-jaw))
            if best is None or score>best[0]:
                best=(score,q,rod,xy,jaw,margin)
    if best is None or best[0]<0.:
        raise ValueError("C11_NO_HIGH_GOAL_WITH_ORIGINAL_BIN_AND_STRICT_5MM_XY")
    _,q,rod,xy,jaw,margin=best
    return {"joint_goal":q,"predicted_rod_world_xyz_m":rod,
            "predicted_bin_xy_error_m":xy,
            "predicted_jaw_world_change_rad":jaw,
            "original_link4_bin_sat_margin_m":margin,
            "bounded_candidates_checked":trials,
            "requires_moveit_plan_only_before_real_goal":True,
            "G04B":"BLOCKED_PENDING_NATIVE_PHYSICS"}
