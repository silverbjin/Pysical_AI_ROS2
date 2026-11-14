#!/usr/bin/env python3
"""TDD: one 2mm real FJT for BOTH fingers before MoveGroup and contact."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_physical_preload_contract import FINGERS,EXPECTED_PRELOAD_M,actual_preload_pass
class RealBilateralPreloadTDD(unittest.TestCase):
 def setUp(self):
  self.goal={n:.002 for n in FINGERS}
  self.measured={"joint_finger1":.00197,"joint_finger2":.0019}
  self.ok={"name":"lower_stop_release_both_fingers_2mm",
    "status":4,"result_error":0,"command_by_joint_m":dict(self.goal),
    "actual_m":dict(self.measured),"joint_tracking_pass":True}
 def test_both_real_fingers_released_before_movegroup_and_grasp(self):
  self.assertTrue(actual_preload_pass(self.ok,dict(self.goal),dict(self.goal)))
 def test_finger1_left_at_zero_fails_even_if_finger2_moves(self):
  actual=dict(self.measured,joint_finger1=0.)
  case=dict(self.ok,actual_m=actual)
  self.assertFalse(actual_preload_pass(case,self.goal,self.goal))
 def test_finger2_left_at_zero_fails_even_if_finger1_moves(self):
  actual=dict(self.measured,joint_finger2=0.)
  self.assertFalse(actual_preload_pass(dict(self.ok,actual_m=actual),
                                       self.goal,self.goal))
 def test_movegroup_cannot_lose_either_preload(self):
  for n in FINGERS:
   measured=dict(self.goal);measured[n]=0.
   self.assertFalse(actual_preload_pass(self.ok,measured,self.goal))
   self.assertFalse(actual_preload_pass(self.ok,self.goal,measured))
 def test_false_action_green_is_blocked(self):
  self.assertFalse(actual_preload_pass(dict(self.ok,status=6),self.goal,self.goal))
  self.assertFalse(actual_preload_pass(dict(self.ok,actual_m=None),self.goal,self.goal))
  self.assertFalse(actual_preload_pass(self.ok,None,self.goal))
 def test_no_unilateral_preload_or_tolerance_relaxation(self):
  self.assertEqual(EXPECTED_PRELOAD_M,.002)
  desired=dict(self.goal);desired["joint_finger1"]=0.0
  self.assertFalse(actual_preload_pass(dict(self.ok,command_by_joint_m=desired),self.goal,self.goal))
 def test_independent_physics_gates_not_removed_by_preload_fix(self):
  from pathlib import Path
  audit=(Path(__file__).resolve().parents[1]/"ch07_77_g04b_verify_contacts.py").read_text()
  for key in ("real_both_fingers_positive_force",
              "real_dynamic_world_lift_at_least_0_05m",
              "1_3s_hold_pose_drift_le_0_025m",
              "no_wrist_rod_collision_in_entire_physical_sequence",
              "placement_xy_error_le_0_09m"):
   self.assertIn(key,audit)
if __name__=="__main__":unittest.main()
