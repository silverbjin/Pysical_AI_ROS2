"""Cycle18 C17 original wrist collision→physical withdrawal L0."""
import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_release_wrist_retract import (
 original_wrist_against_falling_rod_sat_margin,source_release_wrist_retract,
 Q3_WITHDRAWAL_RAD,C19_RETRACT_FJT_DURATION_S,
 C19_CONSERVATIVE_PEAK_VELOCITY_RAD_S,SOURCE_Q3_MAX_VELOCITY_RAD_S)
Q={"joint1":0.5091643923439638,"joint2":-0.3311969830375786,
   "joint3":1.0495678953415792,"joint4":1.5691681973423308,
   "joint_wrist":-0.3460610190425167}
ROD=[0.503606,0.238149,1.91499]
SCENE={"id":"g04b_existing_gazebo_bin_collision","frame_id":"base_link",
 "center_m":[.55,.25,1.63],"box_m":[.30,.30,.20],
 "bin_yaw_rad":.35,"source":"ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED",
 "apply_planning_scene_success":True}
class Cycle18ReleaseWithdraw(unittest.TestCase):
 def test_c17_pre_release_wrist_occludes_actual_drop_path(self):
  m=original_wrist_against_falling_rod_sat_margin(Q,ROD)
  self.assertLess(m,-.020) # conservative AABB, actual 648 wrist strikes
 def test_c18_bounded_wrist_withdrawal_only_after_real_native_rod(self):
  x=source_release_wrist_retract(Q,ROD,SCENE)
  self.assertEqual(x["retract_joint"],"joint3")
  self.assertAlmostEqual(x["target"]["joint3"],Q["joint3"]-.055)
  for name in Q:
   if name!="joint3":self.assertEqual(Q[name],x["target"][name])
  self.assertGreater(x["predicted_wrist_retreat_xy_m"],.041)
  self.assertGreater(x["predicted_wrist_retreat_up_m"],.03)
  self.assertGreater(x["conditional_static_rod_drop_after_sat_m"],.008)
  self.assertGreater(x["min_original_bin_link4_path_sat_m"],.003)
  self.assertTrue(x["requires_true_native_zero_wrist_rod_contact"])
  self.assertEqual(x["status"],"L0_KINEMATIC_ONLY_G04B_BLOCKED")
 def test_original_q3_speed_limit_and_witness_one_duration(self):
  self.assertAlmostEqual(C19_RETRACT_FJT_DURATION_S,.25)
  self.assertLess(C19_CONSERVATIVE_PEAK_VELOCITY_RAD_S,
                  SOURCE_Q3_MAX_VELOCITY_RAD_S)
  witness=(Path(__file__).resolve().parents[1]/
           "ch07_77_g04b_actual_physics_witness.py").read_text()
  self.assertIn("ap.time_from_start.nanosec=int(C19_RETRACT_FJT_DURATION_S*1e9)",witness)
  self.assertIn("gp.time_from_start.sec=2",witness)
  audit=(Path(__file__).resolve().parents[1]/
         "ch07_77_g04b_verify_contacts.py").read_text()
  self.assertIn("no_wrist_rod_collision_in_entire_physical_sequence",audit)
  self.assertIn("wrist_rod_collision_events==0",audit)

 def test_geometry_or_missing_scene_never_accepted(self):
  for ch in ({"bin_yaw_rad":0.},{"box_m":[.28,.30,.20]},
             {"center_m":[.55,.25,1.64]},
             {"apply_planning_scene_success":False},
             {"source":"ORIGINAL_STATIC_GAZEBO_BIN"}):
   with self.assertRaises(ValueError):
    source_release_wrist_retract(Q,ROD,{**SCENE,**ch})
 def test_bad_rod_and_arm_fail_closed(self):
  for q,rod in ((Q,[.75,.25,1.91]),(Q,[.503,.238,1.7]),
                ({"joint1":0.},ROD),
                ({**Q,"joint3":math.nan},ROD),
                (Q,[.503,float("nan"),1.91])):
   with self.assertRaises(ValueError):
    source_release_wrist_retract(q,rod,SCENE)
if __name__=="__main__":unittest.main()
