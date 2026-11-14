#!/usr/bin/env python3
import pathlib,sys,unittest,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_bin_transport_contract import (
 corrected_high_target,feedback_centered_high_target,
 custody_offset,custody_drift,high_arrival_valid,precise_high_arrival_valid,
 pre_release_valid,LOWER_WRIST_Z,historical_wrist_bias_lower_goal,
 actual_finger_tilt_drift)
from ch07_181_exact_fk import actual_tool_axis_angle_rad
FRESH={"both_native_fresh_positive_force":True,
 "per_finger":{"finger1":{"recent_contact_events":10},
               "finger2":{"recent_contact_events":10}}}
class WorldPoseTransportTDD(unittest.TestCase):
 def test_world_pose_based_high_wrist_target(self):
  p=corrected_high_target((.528212,-.006809,2.07042))
  self.assertAlmostEqual(p[0],.501788)
  self.assertAlmostEqual(p[1],.256809)
  self.assertEqual(p[2],1.96)
  self.assertEqual(LOWER_WRIST_Z,1.72)
 def test_actual_failed_high_xy_error_generates_single_bounded_correction(self):
  p=feedback_centered_high_target(
      [.489288,.236601,1.96],[.487758,.259155,2.07719])
  self.assertAlmostEqual(p[0],.55153)
  self.assertAlmostEqual(p[1],.227446)
  self.assertEqual(p[2],1.96)
  self.assertFalse(precise_high_arrival_valid([.487758,.259155,2.07719],.004))
  self.assertTrue(precise_high_arrival_valid([.550,.250,2.076],.004))
 def test_missing_bounded_or_unheld_rod_refused(self):
  for p in ((-.4,-.4,2.07),(.53,0,1.80),(float("nan"),0,2.07)):
   with self.subTest(p=p),self.assertRaises(ValueError):
    corrected_high_target(p)
  with self.assertRaises(ValueError):
   feedback_centered_high_target([.489,.237,1.96],[.44,.10,2.08])
 def test_original_transfer_slip_proven(self):
  offset=custody_offset((.528385,-.006804,2.07032),(.537285,-.009753,2.048886))
  self.assertGreater(custody_drift((.642772,.088063,1.83891),
                    (.563734,.269913,1.82261),offset),.10)
 def test_historical_scalar_wrist_bias_is_not_true_world_orientation(self):
  high={"joint1":.47568893843137255,"joint2":.0350878984216544,
      "joint3":.47556993865768904,"joint4":1.5401768852543665,
      "joint_wrist":.027488374531465038}
  low={"joint1":.4519471817202453,"joint2":-.41587467116618015,
     "joint3":1.2525373207617017,"joint4":1.570171588557174,
     "joint_wrist":-.30062985152400895}
  self.assertLess(actual_finger_tilt_drift(high,low),.003)
  self.assertGreater(actual_tool_axis_angle_rad(high,low),.46)
 def test_historical_wrist_target_not_silently_clamped(self):
  held={"joint1":0.,"joint2":0.,"joint3":0.,
        "joint4":1.5708,"joint_wrist":-1.2}
  lower={"joint1":0.,"joint2":-.5,"joint3":1.4,
         "joint4":1.5708,"joint_wrist":0.}
  with self.assertRaisesRegex(ValueError,"WRIST_PITCH_COMPENSATION_LIMIT"):
   historical_wrist_bias_lower_goal(held,lower)
 def test_old_failed_release_pose_cannot_pass_even_with_contacts(self):
  self.assertFalse(pre_release_valid((.642772,.088063,1.83891),FRESH))
 def test_real_native_contact_required_not_action_green(self):
  self.assertTrue(pre_release_valid((.552,.248,1.83),FRESH))
  self.assertFalse(pre_release_valid((.552,.248,1.83),None))
  fake={"both_native_fresh_positive_force":True,
        "per_finger":{"finger1":{"recent_contact_events":10},
                      "finger2":{"recent_contact_events":0}}}
  self.assertFalse(pre_release_valid((.552,.248,1.83),fake))
 def test_high_and_low_guards_distinct(self):
  self.assertTrue(high_arrival_valid((.552,.248,2.063),.012))
  self.assertFalse(pre_release_valid((.552,.248,2.063),FRESH))
  self.assertTrue(pre_release_valid((.552,.248,1.83),FRESH))
  self.assertFalse(pre_release_valid((.552,.248,1.70),FRESH))
if __name__=="__main__":unittest.main()
