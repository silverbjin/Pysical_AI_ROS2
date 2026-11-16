"""C12 actual held-rod IK for same solid box yaw-only setup; L0/FCL guard."""
import math
from ch07_181_exact_fk import original_finger_collision_center,actual_tool_axis_angle_rad
from ch07_181_jaw_axis_carry import real_jaw_world_axis_change
from ch07_181_high_goal_precision_contract import (
 HIGH_FK_BIN_TARGET_MAX_ERROR_M,assess_precise_high_arrival)
from ch07_181_clearance_verified_high import valid_arm,original_link4_bin_sat_margin
ARM=("joint1","joint2","joint3","joint4","joint_wrist")
SEED=(.45513094,.00642095,.57534782,1.41250335,-.18389185)
def source_bin_rotated_high_goal(held,rod,scene):
 if not valid_arm(held) or not isinstance(rod,(list,tuple)) or len(rod)!=3:
  raise ValueError("C12_HELD_INPUT_INVALID")
 if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in rod):
  raise ValueError("C12_NONFINITE_ROD")
 if (not isinstance(scene,dict) or scene.get("apply_planning_scene_success") is not True
     or scene.get("id")!="g04b_existing_gazebo_bin_collision"
     or scene.get("frame_id")!="base_link"
     or tuple(scene.get("center_m",()))!=(.55,.25,1.63)
     or tuple(scene.get("box_m",()))!=(.30,.30,.20)
     or scene.get("bin_yaw_rad")!=.35
     or scene.get("source")!="ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED"):
  raise ValueError("C12_STATIC_SCENE_ROLL_PITCH_SHAPE_OR_YAW_MISMATCH")
 f=original_finger_collision_center(held)
 off=[rod[k]-f[k] for k in range(3)]
 if math.sqrt(sum(v*v for v in off))>.055:raise ValueError("C12_NOT_REAL_HELD_ROD")
 q=dict(zip(ARM,SEED))
 for _ in range(8):
  p=original_finger_collision_center(q)
  ex=.55-p[0]-off[0];ey=.25-p[1]-off[1]
  if math.hypot(ex,ey)<1e-8:break
  h=1e-5
  a=original_finger_collision_center({**q,"joint1":q["joint1"]+h})
  b=original_finger_collision_center({**q,"joint3":q["joint3"]+h})
  aa=(a[0]-p[0])/h;bb=(b[0]-p[0])/h
  cc=(a[1]-p[1])/h;dd=(b[1]-p[1])/h
  det=aa*dd-bb*cc
  if abs(det)<1e-9:raise ValueError("C12_IK_JACOBIAN_SINGULAR")
  q["joint1"]+=max(-.08,min(.08,(dd*ex-bb*ey)/det))
  q["joint3"]+=max(-.08,min(.08,(-cc*ex+aa*ey)/det))
 p=original_finger_collision_center(q)
 predicted=[p[k]+off[k] for k in range(3)]
 xy=math.hypot(predicted[0]-.55,predicted[1]-.25)
 jaw=real_jaw_world_axis_change(held,q)
 tool=actual_tool_axis_angle_rad(held,q)
 margin=original_link4_bin_sat_margin(q,bin_yaw_rad=.35)
 if (abs(q["joint1"]-SEED[0])>.10 or not .35<q["joint3"]<.90
     or xy>HIGH_FK_BIN_TARGET_MAX_ERROR_M
     or jaw>.25 or tool>.38 or predicted[2]<1.98 or margin<.003):
  raise ValueError("C12_REAL_BIN_HIGH_SAFETY_OR_5MM_PREPLAN_UNPROVEN")
 if not assess_precise_high_arrival(q,q,off)["real_arm_tracking_scoped_pass"]:
  raise ValueError("C12_SOURCE_5MM_ORACLE_FAILED")
 return {"joint_goal":q,"predicted_rod_xyz_m":predicted,
   "strict_bin_xy_error_m":xy,"jaw_world_change_rad":jaw,
   "tool_axis_change_rad":tool,"real_rotated_bin_sat_margin_m":margin,
   "world_single_factor":"BIN_YAW_0_TO_0.35_REAL_SOLID_BOX",
   "requires_moveit_plan_only_before_real_motion":True,
   "G04B":"BLOCKED_UNTIL_NATIVE_CONTACT_RELEASE_ROI_PASS"}
