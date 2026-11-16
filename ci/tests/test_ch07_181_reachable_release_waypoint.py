#!/usr/bin/env python3
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_reachable_release_waypoint import (
    reachable_release_waypoint,SAFE_Q3_RAD)
HIGH={"joint1":.41728596767889253,"joint2":.08702368253198478,
      "joint3":.4341828087408462,"joint4":1.190934872651502,
      "joint_wrist":-.00035816131222489726}
LOW={"joint1":.42331937459042024,"joint2":-.40336640985894334,
     "joint3":1.2531741401339573,"joint4":1.2046139339250965,
     "joint_wrist":-.12220232798615689}
OFFSET=[-.0020738385782899105,.001257711179281128,.01788613884643686]
class ReachableReleaseTDD(unittest.TestCase):
 def test_native_high_pose_bounded_reachable_center(self):
  x=reachable_release_waypoint(HIGH,LOW,OFFSET)
  self.assertAlmostEqual(x["target"]["joint3"],1.05,places=6)
  self.assertLess(x["predicted_bin_xy_error_m"],.015)
  self.assertTrue(1.87<=x["predicted_rod_world_xyz_m"][2]<=1.92)
  self.assertTrue(.10<=x["predicted_release_drop_m"]<=.16)
  self.assertLess(x["world_jaw_change_rad"],1e-5)
  self.assertLess(x["world_tool_change_rad"],.38)
  self.assertEqual(x["scope"],"KINEMATIC_ONLY_NOT_PHYSICAL_ACCEPTANCE")
 def test_missing_or_unsafe_input_fails_closed(self):
  for high,low,offset in [
    ({"joint1":0.},LOW,OFFSET),
    (HIGH,dict(LOW,joint3=float("nan")),OFFSET),
    (HIGH,LOW,[float("inf"),0.,0.]),
    (HIGH,LOW,[.25,.25,.25]),
    (HIGH,dict(LOW,joint3=1.10),OFFSET)]:
   with self.assertRaises(ValueError):
    reachable_release_waypoint(high,low,offset)
 def test_pure_inputs_and_strict_real_joint_state_admission(self):
  a,b,c=dict(HIGH),dict(LOW),list(OFFSET)
  reachable_release_waypoint(a,b,c)
  self.assertEqual((a,b,c),(HIGH,LOW,OFFSET))
  self.assertEqual(SAFE_Q3_RAD,1.05)
  witness=(Path(__file__).resolve().parents[1]/
           "ch07_77_g04b_actual_physics_witness.py").read_text()
  self.assertIn("lower_reachable_release_actual_joint_errors_rad",witness)
  self.assertIn("JOINT_GOAL_TOL_RAD",witness)
if __name__=="__main__":unittest.main()
