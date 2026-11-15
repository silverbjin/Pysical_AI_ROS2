#!/usr/bin/env python3
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_high_goal_precision_contract import (
 assess_precise_high_arrival,HIGH_MOVEGROUP_JOINT_CONSTRAINT_RAD,
 HIGH_ACTUAL_JOINT_MAX_ERROR_RAD,high_settle_recovery_eligible,
 HIGH_SETTLE_MAX_INITIAL_ERROR_RAD,HIGH_SETTLE_SAFE_BIN_XY_M)
GOAL={"joint1":.423610,"joint2":.100500,"joint3":.430060,
      "joint4":1.5707963267948966,"joint_wrist":0.0}
FAILED={"joint1":.3900264650883941,"joint2":.06922524068895992,
        "joint3":.45028819611891974,"joint4":1.5662761685661466,
        "joint_wrist":.027541191341996115}
HELD_OFFSET=(-.003151903410560264,.0005792944519445297,.018962336003945257)
class HighActualArmTDD(unittest.TestCase):
 def test_previous_movegroup_succeeded_but_34mrad_arm_error_fails(self):
  r=assess_precise_high_arrival(GOAL,FAILED,HELD_OFFSET)
  self.assertGreater(r["max_joint_error_rad"],.03)
  self.assertFalse(r["real_arm_tracking_scoped_pass"])
 def test_original_measured_joint_target_nearly_exact_is_eligible(self):
  near=dict(GOAL)
  near["joint1"]-=.001
  near["joint2"]+=.001
  near["joint3"]-=.0005
  r=assess_precise_high_arrival(GOAL,near,HELD_OFFSET)
  self.assertTrue(r["real_arm_tracking_scoped_pass"])
 def test_missing_joints_and_bad_held_offsets_fail_closed(self):
  with self.assertRaises(ValueError):
   assess_precise_high_arrival({"joint1":0},FAILED,HELD_OFFSET)
  with self.assertRaises(ValueError):
   assess_precise_high_arrival(GOAL,GOAL,(float("nan"),0.,0.))
 def test_movegroup_precision_not_relaxed_from_existing_alignment(self):
  self.assertEqual(HIGH_MOVEGROUP_JOINT_CONSTRAINT_RAD,.002)
  self.assertEqual(HIGH_ACTUAL_JOINT_MAX_ERROR_RAD,.01)
class HighSmallLagRecoveryTDD(unittest.TestCase):
 def test_actual_raw_13mrad_lag_native_rod_inside_safe_bin(self):
  # Raw #43713755831, source frozen original in immutable artifact.
  a={"per_joint_error_rad":{
    "joint1":.00011003967522554836,
    "joint2":.013284449200135662,
    "joint3":.0011358572991028715,
    "joint4":.0019109292381014331,
    "joint_wrist":.0014019248178159566}}
  self.assertTrue(high_settle_recovery_eligible(a,[.530989,.244177,2.07302]))
 def test_large_or_nonfinite_or_missing_is_not_eligible(self):
  for bad in (.034,float("inf"),float("nan"),-.1):
   a={"per_joint_error_rad":{n:.001 for n in GOAL}}
   a["per_joint_error_rad"]["joint2"]=bad
   self.assertFalse(high_settle_recovery_eligible(a,[.53,.24,2.07]))
  self.assertFalse(high_settle_recovery_eligible({"per_joint_error_rad":{"joint1":.015}},[.53,.24,2.07]))
 def test_object_outside_original_envelope_blocks_correction(self):
  a={"per_joint_error_rad":{n:.013 for n in GOAL}}
  for xyz in ([.7,.25,2.07],[.53,.24,1.8],[float("nan"),.25,2.07]):
   self.assertFalse(high_settle_recovery_eligible(a,xyz))
 def test_original_precision_not_relaxed(self):
  self.assertEqual(HIGH_ACTUAL_JOINT_MAX_ERROR_RAD,.01)
  self.assertEqual(HIGH_SETTLE_MAX_INITIAL_ERROR_RAD,.02)
  self.assertEqual(HIGH_SETTLE_SAFE_BIN_XY_M,.09)
 def test_no_extra_goal_for_already_precise_joint_feedback(self):
  a={"per_joint_error_rad":{n:.001 for n in GOAL}}
  self.assertFalse(high_settle_recovery_eligible(a,[.55,.25,2.08]))
if __name__=="__main__":unittest.main()
