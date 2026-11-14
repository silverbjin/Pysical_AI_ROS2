#!/usr/bin/env python3
import pathlib,sys,unittest,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_bin_transport_contract import (
 corrected_high_target,exact_fk_high_bin_wrist_target,
 feedback_centered_high_target,custody_offset,custody_drift,
 high_arrival_valid,precise_high_arrival_valid,pre_release_valid,
 LOWER_WRIST_Z,historical_wrist_bias_lower_goal,actual_finger_tilt_drift)
from ch07_181_exact_fk import actual_tool_axis_angle_rad
FRESH={"both_native_fresh_positive_force":True,
 "per_finger":{"finger1":{"recent_contact_events":10},
               "finger2":{"recent_contact_events":10}}}
HELD={"joint1":.0049887683889259715,"joint2":-.027408629093679433,
      "joint3":.6004212758813569,"joint4":1.5499237313811005,
      "joint_wrist":-.002528481677278027}
class WorldPoseTransportTDD(unittest.TestCase):
 def test_true_fk_high_target_from_actual_held_cylinder(self):
  goal=exact_fk_high_bin_wrist_target(HELD,[.572967,.003382,2.04838])
  self.assertAlmostEqual(goal[0],.513603,places=4)
  self.assertAlmostEqual(goal[1],.228741,places=4)
  self.assertEqual(goal[2],1.96)
 def test_detached_cylinder_cannot_become_a_fake_high_plan(self):
  with self.assertRaises(ValueError):
   exact_fk_high_bin_wrist_target(HELD,[.595335,.106504,2.06834])
 def test_historical_frozen_lift_guess_was_wrong(self):
  p=corrected_high_target((.528212,-.006809,2.07042))
  self.assertAlmostEqual(p[0],.501788)
  self.assertAlmostEqual(p[1],.256809)
  self.assertEqual(LOWER_WRIST_Z,1.72)
 def test_fallback_bounded_real_high_feedback_correction(self):
  p=feedback_centered_high_target(
      [.489288,.236601,1.96],[.487758,.259155,2.07719])
  self.assertAlmostEqual(p[0],.55153)
  self.assertAlmostEqual(p[1],.227446)
  self.assertFalse(precise_high_arrival_valid([.487758,.259155,2.07719],.004))
  self.assertTrue(precise_high_arrival_valid([.550,.250,2.076],.004))
  with self.assertRaises(ValueError):
   feedback_centered_high_target([.489,.237,1.96],[.44,.10,2.08])
 def test_unbounded_or_nonfinite_held_state_rejected(self):
  with self.assertRaises(ValueError):
   exact_fk_high_bin_wrist_target(HELD,[float("nan"),0,2.07])
 def test_actual_previous_transfer_custody_error_detected(self):
  offset=custody_offset((.528385,-.006804,2.07032),(.537285,-.009753,2.048886))
  self.assertGreater(custody_drift((.642772,.088063,1.83891),
                    (.563734,.269913,1.82261),offset),.10)
 def test_scalar_wrist_sum_did_not_preserve_world_orientation(self):
  high={"joint1":.47568893843137255,"joint2":.0350878984216544,
      "joint3":.47556993865768904,"joint4":1.5401768852543665,
      "joint_wrist":.027488374531465038}
  low={"joint1":.4519471817202453,"joint2":-.41587467116618015,
     "joint3":1.2525373207617017,"joint4":1.570171588557174,
     "joint_wrist":-.30062985152400895}
  self.assertLess(actual_finger_tilt_drift(high,low),.003)
  self.assertGreater(actual_tool_axis_angle_rad(high,low),.46)
 def test_historical_bias_never_silently_clamped(self):
  held={"joint1":0.,"joint2":0.,"joint3":0.,
        "joint4":1.5708,"joint_wrist":-1.2}
  lower={"joint1":0.,"joint2":-.5,"joint3":1.4,
         "joint4":1.5708,"joint_wrist":0.}
  with self.assertRaisesRegex(ValueError,"WRIST_PITCH_COMPENSATION_LIMIT"):
   historical_wrist_bias_lower_goal(held,lower)
 def test_old_release_pose_cannot_pass_even_with_force(self):
  self.assertFalse(pre_release_valid((.642772,.088063,1.83891),.01,FRESH))
 def test_missing_native_evidence_or_real_geometry_rejected(self):
  self.assertTrue(pre_release_valid((.552,.248,1.83),.008,FRESH))
  self.assertFalse(pre_release_valid((.552,.248,1.83),.008,None))
  self.assertFalse(pre_release_valid((.552,.248,1.83),.213356,FRESH))
  self.assertFalse(pre_release_valid((.552,.248,1.83),float("nan"),FRESH))
  fake={"both_native_fresh_positive_force":True,
        "per_finger":{"finger1":{"recent_contact_events":10},
                      "finger2":{"recent_contact_events":0}}}
  self.assertFalse(pre_release_valid((.552,.248,1.83),.008,fake))
 def test_high_and_low_guards_distinct(self):
  self.assertTrue(high_arrival_valid((.552,.248,2.063),.012))
  self.assertFalse(pre_release_valid((.552,.248,2.063),.008,FRESH))
  self.assertTrue(pre_release_valid((.552,.248,1.83),.008,FRESH))
  self.assertFalse(pre_release_valid((.552,.248,1.70),.008,FRESH))
if __name__=="__main__":unittest.main()
