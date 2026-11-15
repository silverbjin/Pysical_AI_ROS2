#!/usr/bin/env python3
"""Issue #181 one-factor test: 2mm lower-stop release ordered by finger."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_physical_preload_contract import (isolated_finger1_release_pass,
                                                 actual_preload_pass)
CI=Path(__file__).resolve().parents[1]
class StaggeredPreloadTDD(unittest.TestCase):
 def setUp(self):
  self.first={"name":"lower_stop_release_finger1_only_2mm",
              "status":4,"result_error":0,"joint_tracking_pass":True,
              "command_by_joint_m":{"joint_finger1":.002,"joint_finger2":0.},
              "actual_m":{"joint_finger1":.00199,"joint_finger2":0.}}
  self.second={"name":"lower_stop_release_both_fingers_2mm",
               "status":4,"result_error":0,"joint_tracking_pass":True,
               "command_by_joint_m":{"joint_finger1":.002,"joint_finger2":.002},
               "actual_m":{"joint_finger1":.002,"joint_finger2":.00199}}
 def test_first_measured_finger1_only_success(self):
  self.assertTrue(isolated_finger1_release_pass(self.first))
  self.assertTrue(actual_preload_pass(self.second,
                self.second["actual_m"],self.second["actual_m"]))
 def test_original_finger1_freeze_fail_closed_before_second_goal(self):
  frozen=dict(self.first,actual_m={"joint_finger1":0.,"joint_finger2":0.})
  self.assertFalse(isolated_finger1_release_pass(frozen))
 def test_no_false_success_from_fjt_only(self):
  for bad in (dict(self.first,status=6),
              dict(self.first,result_error=-5),
              dict(self.first,joint_tracking_pass=False),
              dict(self.first,actual_m={}),
              dict(self.first,actual_m={"joint_finger1":.002,
                                       "joint_finger2":.002})):
   self.assertFalse(isolated_finger1_release_pass(bad))
 def test_both_fingers_still_required_before_movegroup(self):
  bad=dict(self.second,actual_m={"joint_finger1":.002,"joint_finger2":0.})
  self.assertFalse(actual_preload_pass(bad,
                  self.second["actual_m"],self.second["actual_m"]))
 def test_original_native_acceptance_still_strict(self):
  audit=(CI/"ch07_77_g04b_verify_contacts.py").read_text()
  for name in ("real_both_fingers_positive_force",
               "real_dynamic_world_lift_at_least_0_05m",
               "1_3s_hold_pose_drift_le_0_025m",
               "no_wrist_rod_collision_in_entire_physical_sequence",
               "placement_xy_error_le_0_09m"):
   self.assertIn(name,audit)
if __name__=="__main__":unittest.main()
