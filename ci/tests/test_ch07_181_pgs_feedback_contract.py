#!/usr/bin/env python3
import pathlib,sys,unittest,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_pgs_feedback_contract import (
    pgs_bounded_recenter,verify_post_correction)
ARM={"joint1":.4,"joint2":.1,"joint3":.4,
     "joint4":1.15,"joint_wrist":0.0}
class PGSHighFeedbackTDD(unittest.TestCase):
 def test_original_PGS_scoped_high_result_admits_only_one_small_correction(self):
  z=pgs_bounded_recenter(
      [.492,.236,1.96],[.537241,.215016,2.07376],.03703974836,ARM)
  self.assertAlmostEqual(z["real_rod_xy_error_before_m"],.03723804959,places=5)
  self.assertEqual(z["candidate_goal_count"],1)
  self.assertAlmostEqual(z["candidate_wrist_xyz_m"][0],.504759)
  self.assertAlmostEqual(z["candidate_wrist_xyz_m"][1],.270984)
  self.assertEqual(z["held_q4_rad"],1.15)
 def test_original_Dantzig_7cm_bin_miss_cannot_be_retried(self):
  with self.assertRaises(ValueError):
   pgs_bounded_recenter([.50,.24,1.96],[.5408,.178109,2.0757],
                        .07360399,ARM)
 def test_previous_second_correction_5cm_error_disallowed(self):
  with self.assertRaises(ValueError):
   pgs_bounded_recenter([.51,.23,1.96],[.533096,.201403,2.07552],
                        .0257,ARM)
 def test_missing_true_grip_evidence_not_succeeded_action(self):
  with self.assertRaises(ValueError):
   pgs_bounded_recenter([.51,.23,1.96],[.537241,.215016,2.07376],
                        .050,ARM)
 def test_exact_original_success_thresholds_retained(self):
  x=verify_post_correction([.550,.250,2.073],.012,
                           ARM,dict(ARM,joint1=.4004))
  self.assertTrue(x["physical_fine_high_PASS"])
  y=verify_post_correction([.550,.220,2.073],.012,ARM,ARM)
  self.assertFalse(y["physical_fine_high_PASS"])
  z=verify_post_correction([.550,.250,2.073],.050,ARM,ARM)
  self.assertFalse(z["physical_fine_high_PASS"])
 def test_actual_q4_must_remain_tracked_and_original_gripper_unchanged(self):
  self.assertFalse(verify_post_correction(
    [.550,.250,2.073],.010,ARM,dict(ARM,joint4=1.16))["physical_fine_high_PASS"])
if __name__=="__main__":unittest.main()
