#!/usr/bin/env python3
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_physical_preload_contract import EXPECTED_PRELOAD_M,actual_preload_pass
class RealPreloadTDD(unittest.TestCase):
 def setUp(self):
  self.ok={"name":"lower_stop_release_finger2_2mm","status":4,"result_error":0,
    "command_by_joint_m":{"joint_finger1":0.0,"joint_finger2":.002},
    "actual_m":{"joint_finger1":0.0,"joint_finger2":.001998},
    "joint_tracking_pass":True}
 def test_physical_actual_2mm_before_and_after_movegroup(self):
  self.assertTrue(actual_preload_pass(self.ok,.002,.002))
 def test_action_succeeded_but_finger2_at_zero_fails(self):
  broken=dict(self.ok,actual_m={"joint_finger2":0.0})
  self.assertFalse(actual_preload_pass(broken,.002,.002))
 def test_movegroup_lost_preload_fails(self):
  self.assertFalse(actual_preload_pass(self.ok,0.0,.002))
  self.assertFalse(actual_preload_pass(self.ok,.002,0.0))
 def test_no_force_attach_or_loose_gate(self):
  self.assertEqual(EXPECTED_PRELOAD_M,.002)
  bad=dict(self.ok,status=6,result_error=-5)
  self.assertFalse(actual_preload_pass(bad,.002,.002))
 def test_independent_physics_gates_not_removed_by_preload_fix(self):
  source=(pathlib.Path(__file__).resolve().parents[1]/
          "ch07_77_g04b_verify_contacts.py").read_text()
  mandatory=("real_both_fingers_at_least_three_contacts",
    "real_both_fingers_positive_force",
    "real_dynamic_world_lift_at_least_0_05m",
    "1_3s_hold_pose_drift_le_0_025m",
    "placement_xy_error_le_0_09m",
    "placement_height_error_le_0_055m",
    "no_wrist_support_collision_in_entire_trajectory",
    "real_finger2_2mm_before_and_after_movegroup")
  for key in mandatory:
   with self.subTest(key=key):self.assertIn('"'+key+'"',source)
  self.assertIn('actual_preload_pass(',source)
  self.assertIn('"contact_close","release"',source)
  self.assertNotIn('"contact_close_stage1" in',source)
 def test_missing_evidence_fails(self):
  self.assertFalse(actual_preload_pass(None,.002,.002))
  self.assertFalse(actual_preload_pass(self.ok,None,.002))
if __name__=="__main__":unittest.main()
