"""Cycle10: original collision box and native held-offset L0 contracts."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_clearance_verified_high import (
    original_link4_bin_sat_margin,source_bin_clearance_high_goal)
from ch07_181_exact_fk import original_finger_collision_center
HELD={"joint1":-.021604442850938002,"joint2":-.06390928383311037,
      "joint3":.5760590780796367,"joint4":1.5663912464201168,
      "joint_wrist":.013581421757570503}
OFFSET=(-.008080553833572368,.001345377625129195,.019434819979277762)
ROD=[original_finger_collision_center(HELD)[k]+OFFSET[k] for k in range(3)]
SCENE={"id":"g04b_existing_gazebo_bin_collision","frame_id":"base_link",
       "center_m":[.55,.25,1.63],"box_m":[.30,.30,.20],
       "apply_planning_scene_success":True}
class TestClearanceHigh(unittest.TestCase):
 def test_old_both_high_goals_intersect_original_real_bin(self):
  for q in ((.419,.111,.418,1.179,0.),
            (.423773,.648605,-.370351,1.133468,0.)):
   arm=dict(zip(HELD,q))
   self.assertLess(original_link4_bin_sat_margin(arm),0.)
 def test_raw_held_offset_source_box_feasible_but_not_physical_pass(self):
  c=source_bin_clearance_high_goal(HELD,ROD,SCENE)
  self.assertGreater(c["original_link4_bin_sat_margin_m"],.003)
  self.assertLess(c["predicted_bin_xy_error_m"],.025)
  self.assertGreater(c["predicted_rod_world_xyz_m"][2],1.98)
  self.assertTrue(c["requires_moveit_plan_only_before_real_goal"])
  self.assertEqual(c["G04B"],"BLOCKED_PENDING_NATIVE_PHYSICS")
 def test_not_allowed_to_replace_real_bin_or_skip_scene(self):
  for changed in ({"center_m":[.55,.25,1.50]},
                  {"box_m":[.10,.10,.20]},
                  {"apply_planning_scene_success":False}):
   with self.assertRaises(ValueError):
    source_bin_clearance_high_goal(HELD,ROD,{**SCENE,**changed})
 def test_nan_unheld_rod_and_missing_joints_fail_closed(self):
  for arm,rod in ((HELD,[ROD[0]+.2,ROD[1],ROD[2]]),
                  ({**HELD,"joint2":math.nan},ROD),
                  (HELD,[ROD[0],ROD[1],math.nan]),
                  ({"joint1":0.},ROD)):
   with self.assertRaises(ValueError):
    source_bin_clearance_high_goal(arm,rod,SCENE)
if __name__=="__main__":unittest.main()
