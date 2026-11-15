#!/usr/bin/env python3
"""Issue #181: one geometry-grounded compression change; keep real gates."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_symmetric_grasp_contract import (
 ORIGINAL_OPEN_FACE_GAP_M,ROD_DIAMETER_M,
 symmetric_close_joint_target)
class RealContactCompressionTDD(unittest.TestCase):
 def test_raw_geometry_first_face_contact_depth_is_10point5mm(self):
  self.assertAlmostEqual((ORIGINAL_OPEN_FACE_GAP_M-ROD_DIAMETER_M)/2,.0105)
 def test_one_millimeter_bilateral_compression_yields_bounded_11point5mm(self):
  self.assertAlmostEqual(symmetric_close_joint_target(
      ORIGINAL_OPEN_FACE_GAP_M,ROD_DIAMETER_M,
      compression_per_finger_m=.001),.0115)
 def test_historical_11mm_target_was_less_than_new_contact_margin(self):
  self.assertAlmostEqual(symmetric_close_joint_target(),.011)
  self.assertGreater(.0115,.011)
 def test_excessive_compression_still_rejected_by_original_contract(self):
  with self.assertRaises(ValueError):
   symmetric_close_joint_target(
       ORIGINAL_OPEN_FACE_GAP_M,ROD_DIAMETER_M,
       compression_per_finger_m=.00101)
 def test_no_controller_goal_tolerance_or_fake_attach_change(self):
  ci=pathlib.Path(__file__).resolve().parents[1]
  witness=(ci/'ch07_77_g04b_actual_physics_witness.py').read_text()
  verify=(ci/'ch07_77_g04b_verify_contacts.py').read_text()
  self.assertIn('compression_per_finger_m=compression',witness)
  self.assertIn('tolerance_m=.0025 if label=="contact_close" else .001',witness)
  self.assertIn('bounded_real_bilateral_1mm_compression_target',verify)
  for name in ('real_both_fingers_positive_force','real_dynamic_world_lift_at_least_0_05m',
               'dynamic_object_released_in_safe_bin_envelope',
               'no_wrist_rod_collision_in_entire_physical_sequence'):
   self.assertIn(name,verify)
if __name__=='__main__':unittest.main()
