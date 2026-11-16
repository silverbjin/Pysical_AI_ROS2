"""Cycle18: source-based bounded wrist withdrawal during physical release.

Only one new release-stage joint3 FJT goal is prepared. No fake object
attachment, altered Gazebo collision, or relaxed independent native audit.
Conservative swept-rod AABB assumes the real rod remains at pre-release XY.
It is a conditional geometry preview, NOT evidence of achieved separation
during an actual synchronized movement. A real FCL plan_only and native
Gazebo zero wrist-rod contact are still mandatory.
"""
import math
from ch07_181_clearance_verified_high import (
    valid_arm, original_link4_bin_sat_margin)
from ch07_181_exact_fk import (
    original_finger_collision_center,original_finger_tool_z_axis)
from ch07_181_jaw_axis_carry import real_jaw_world_axis

Q3_WITHDRAWAL_RAD=.055
C18_ARM_MAX_ERROR_RAD=.01
C18_MIN_SWEPT_CLEARANCE_M=.008
BIN_SETTLED_ROD_Z_M=1.77

def _dot(a,b):
    return sum(x*y for x,y in zip(a,b))

def _cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def _norm(v):
    return math.sqrt(_dot(v,v))

def _wrist_source_pose(q):
    yaw=q["joint1"];q2=q["joint2"];angle=q2+q["joint3"]
    radius=.5*math.sin(q2)+math.sin(angle)
    origin=(radius*math.cos(yaw),radius*math.sin(yaw),
            .6+.5*math.cos(q2)+math.cos(angle))
    x=real_jaw_world_axis(q)
    z=original_finger_tool_z_axis(q)
    y=_cross(z,x)
    axes=(x,y,z)
    center=tuple(origin[i]+.03*z[i] for i in range(3))
    return origin,center,axes

def original_wrist_against_falling_rod_sat_margin(q,rod_xyz):
    """Exact box SAT of original wrist OBB vs CONSERVATIVE drop AABB.

    Source collision box wrist 0.08x0.06x0.06m, centre local +0.03Z.
    Enclosing horizontal rod halfwidth 0.028m (radius .012 and native
    15-degree rod tilt included), vertical halfwidth .04m. Its potential
    vertical translation ends at original 1.77m rod-centre support.
    """
    if not valid_arm(q) or len(rod_xyz)!=3 or not all(
            isinstance(x,(float,int)) and math.isfinite(x)
            for x in rod_xyz):
        raise ValueError("C18_ORIGINAL_WRIST_OR_ROD_INPUT_INVALID")
    if not 1.78<=rod_xyz[2]<=1.92:
        raise ValueError("C18_RELEASE_ROD_HEIGHT_OUTSIDE_SOURCE_GATE")
    _,center,axes=_wrist_source_pose(q)
    drop=max(0.,rod_xyz[2]-BIN_SETTLED_ROD_Z_M)
    rod_center=(rod_xyz[0],rod_xyz[1],rod_xyz[2]-drop/2)
    rod_half=(.028,.028,.04+drop/2)
    world=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    normals=list(axes)+list(world)
    for a in axes:
        for b in world:
            c=_cross(a,b)
            length=_norm(c)
            if length>1e-10:
                normals.append(tuple(t/length for t in c))
    delta=tuple(rod_center[i]-center[i] for i in range(3))
    margin=-float("inf")
    for n in normals:
        wr=sum(s*abs(_dot(u,n)) for u,s in zip(axes,(.04,.03,.03)))
        rr=sum(s*abs(_dot(u,n)) for u,s in zip(world,rod_half))
        margin=max(margin,abs(_dot(delta,n))-wr-rr)
    return margin

def source_release_wrist_retract(lower_actual,rod_xyz,scene):
    if not valid_arm(lower_actual):
        raise ValueError("C18_ACTUAL_LOWER_JOINTSTATE_INVALID")
    if (not isinstance(rod_xyz,(tuple,list)) or len(rod_xyz)!=3 or
        any(not isinstance(x,(float,int)) or not math.isfinite(x)
            for x in rod_xyz)):
        raise ValueError("C18_ACTUAL_NATIVE_ROD_INVALID")
    if (not isinstance(scene,dict) or
        scene.get("apply_planning_scene_success") is not True or
        scene.get("id")!="g04b_existing_gazebo_bin_collision" or
        scene.get("frame_id")!="base_link" or
        tuple(scene.get("center_m",()))!=(.55,.25,1.63) or
        tuple(scene.get("box_m",()))!=(.30,.30,.20) or
        scene.get("bin_yaw_rad")!=.35 or
        scene.get("source")!="ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED"):
        raise ValueError("C18_SOURCE_ORIGINAL_SOLID_BIN_UNPROVEN")
    if (math.hypot(rod_xyz[0]-.55,rod_xyz[1]-.25)>.06 or
        not 1.78<=rod_xyz[2]<=1.92):
        raise ValueError("C18_ROD_NOT_IN_ORIGINAL_PRE_RELEASE_GATE")
    if not (-.45<lower_actual["joint2"]<-.20 and
            .94<lower_actual["joint3"]<=1.05):
        raise ValueError("C18_LOWER_NOT_IN_BOUNDED_SOURCE_STAGE")
    target=dict(lower_actual)
    target["joint3"]-=Q3_WITHDRAWAL_RAD
    # Original link4 versus real solid bin, sampling the direct FJT path.
    margins=[]
    for i in range(17):
        t=i/16
        q={n:lower_actual[n]+t*(target[n]-lower_actual[n])
           for n in lower_actual}
        margins.append(original_link4_bin_sat_margin(q,bin_yaw_rad=.35))
    if min(margins)<.003:
        raise ValueError("C18_RETRACT_FJT_SOURCE_BIN_PATH_COLLIDES")
    start_origin,_,_=_wrist_source_pose(lower_actual)
    end_origin,_,_=_wrist_source_pose(target)
    retreat_xy=math.hypot(end_origin[0]-start_origin[0],
                           end_origin[1]-start_origin[1])
    retreat_z=end_origin[2]-start_origin[2]
    margin=original_wrist_against_falling_rod_sat_margin(target,rod_xyz)
    before=original_wrist_against_falling_rod_sat_margin(lower_actual,rod_xyz)
    if (retreat_xy<.041 or retreat_z<.030 or
        margin<C18_MIN_SWEPT_CLEARANCE_M):
        raise ValueError("C18_WITHDRAWAL_SOURCE_DROP_PATH_NOT_SEPARATED")
    return {
        "target":target,"retract_joint":"joint3",
        "joint3_delta_rad":-Q3_WITHDRAWAL_RAD,
        "predicted_wrist_retreat_xy_m":retreat_xy,
        "predicted_wrist_retreat_up_m":retreat_z,
        "original_wrist_rod_vertical_drop_before_sat_m":before,
        "conditional_static_rod_drop_after_sat_m":margin,
        "min_original_bin_link4_path_sat_m":min(margins),
        "original_held_rod_xyz_m":list(rod_xyz),
        "requires_fcl_plan_only_before_simultaneous_fjt":True,
        "requires_true_native_zero_wrist_rod_contact":True,
        "physical_custody_motion_not_predicted":True,
        "status":"L0_KINEMATIC_ONLY_G04B_BLOCKED"}
