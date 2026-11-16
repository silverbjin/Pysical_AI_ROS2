"""Cycle16 original solid-bin safe lower: C15 physical RED and bounds."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_original_bin_safe_lower import collision_safe_lower_target
from ch07_181_clearance_verified_high import original_link4_bin_sat_margin
from ch07_181_exact_fk import original_finger_collision_center

# C15 native high actual JointState *at start of failed lower*;
# real held offset from same C15 original run. Do not substitute a
# previous run's frozen grasp measurement or fabricated joint response.
C15_HIGH={"joint1":0.45867911551832385,
          "joint2":0.010816514508649103,
          "joint3":0.5668740999625674,
          "joint4":1.4093161899510658,
          "joint_wrist":-0.19349180218478845}
C15_HELD_OFFSET=[-0.003923807540466395,
                 0.0007880586433471302,0.018865788788781312]
C15_COLLIDING_LOWER={"joint1":0.4582366755370468,
                      "joint2":-0.29408633772059967,
                      "joint3":1.05,
                      "joint4":1.4466501932664368,
                      "joint_wrist":-0.2186563621337903}
SCENE={"id":"g04b_existing_gazebo_bin_collision","frame_id":"base_link",
       "center_m":[.55,.25,1.63],"box_m":[.30,.30,.20],
       "bin_yaw_rad":.35,"source":"ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED",
       "apply_planning_scene_success":True}

class TestCycle16SolidLower(unittest.TestCase):
 def test_actual_c15_lower_collides_with_exact_real_link4_solid_bin(self):
  self.assertLess(original_link4_bin_sat_margin(
      C15_COLLIDING_LOWER,bin_yaw_rad=.35),-.03)

 def test_one_safe_lower_candidate_with_real_held_offset_not_physical_pass(self):
  p=collision_safe_lower_target(C15_HIGH,C15_HELD_OFFSET,SCENE)
  self.assertLess(p["predicted_bin_xy_error_m"],.055)
  self.assertGreaterEqual(p["predicted_rod_world_xyz_m"][2],1.80)
  self.assertLessEqual(p["predicted_rod_world_xyz_m"][2],1.915)
  self.assertGreater(p["original_solid_bin_link4_sat_clearance_m"],.0045)
  self.assertGreater(p["preview_min_link4_bin_clearance_m"],.003)
  self.assertLess(p["world_jaw_change_rad"],.245)
  self.assertLess(p["world_tool_change_rad"],.375)
  self.assertLessEqual(p["target"]["joint3"],1.05)
  self.assertTrue(p["requires_independent_moveit_plan_only_before_real_goal"])
  self.assertEqual(p["scope"],"KINEMATIC_ONLY_NOT_PHYSICAL_ACCEPTANCE")
  q=p["target"]
  expected=original_finger_collision_center(q)
  self.assertLess(math.dist([expected[i]+C15_HELD_OFFSET[i]
                             for i in range(3)],p["predicted_rod_world_xyz_m"]),1e-7)

 def test_unproved_planning_scene_and_changed_original_bin_fail_closed(self):
  for change in ({"box_m":[.2,.3,.2]},
                 {"center_m":[.55,.25,1.61]},
                 {"bin_yaw_rad":0.},
                 {"source":"ORIGINAL_STATIC_GAZEBO_BIN"},
                 {"apply_planning_scene_success":False}):
   with self.assertRaises(ValueError):
    collision_safe_lower_target(C15_HIGH,C15_HELD_OFFSET,{**SCENE,**change})

 def test_missing_or_nan_joint_state_or_unheld_rod_fail_closed(self):
  for arm,offset in ((C15_HIGH,[.2,0,0]),
                     ({**C15_HIGH,"joint3":float("nan")},C15_HELD_OFFSET),
                     ({"joint1":.0},C15_HELD_OFFSET),
                     (C15_HIGH,[0.,float("nan"),0.])):
   with self.assertRaises(ValueError):
    collision_safe_lower_target(arm,offset,SCENE)

if __name__=="__main__":unittest.main()
