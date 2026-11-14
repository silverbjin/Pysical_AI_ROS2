#!/usr/bin/env python3
"""TDD from CI #43600241307 measured arm/rod/native Gazebo data."""
import math,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_exact_fk import (original_finger_collision_center,
  original_finger_tool_z_axis,actual_tool_axis_angle_rad)
HIGH={"joint1":.47568893843137255,"joint2":.0350878984216544,
      "joint3":.47556993865768904,"joint4":1.5401768852543665,
      "joint_wrist":.027488374531465038}
LOW={"joint1":.4519471817202453,"joint2":-.41587467116618015,
     "joint3":1.2525373207617017,"joint4":1.570171588557174,
     "joint_wrist":-.30062985152400895}
class ExactOriginalUrdfFkTDD(unittest.TestCase):
 def test_precise_actual_link_fk_at_original_no_wrist_rotation(self):
  actual={"joint1":0.0,"joint2":-.063692118,"joint3":.79020719,
          "joint4":math.pi/2,"joint_wrist":0.0}
  p=original_finger_collision_center(actual)
  self.assertGreater(p[0],.69)
  self.assertLess(p[0],.71)
  self.assertLess(abs(p[1]),.001)
 def test_q4_pi_over_2_turns_wrist_rotation_out_of_arm_pitch_plane(self):
  q={"joint1":0.0,"joint2":0.0,"joint3":0.0,
     "joint4":math.pi/2,"joint_wrist":-.3}
  axis=original_finger_tool_z_axis(q)
  self.assertAlmostEqual(axis[0],0.0,places=7)
  self.assertAlmostEqual(axis[1],math.sin(-.3),places=7)
  self.assertAlmostEqual(axis[2],math.cos(-.3),places=7)
 def test_raw_ci_scalar_tilt_correction_was_not_true_orientation_preservation(self):
  old_arithmetic=abs((HIGH["joint2"]+HIGH["joint3"]+HIGH["joint_wrist"])-
             (LOW["joint2"]+LOW["joint3"]+LOW["joint_wrist"]))
  self.assertLess(old_arithmetic,.003)
  self.assertGreater(actual_tool_axis_angle_rad(HIGH,LOW),.46)
  self.assertLess(actual_tool_axis_angle_rad(HIGH,LOW),.48)
 def test_actual_fk_changed_by_wrist_rotation(self):
  p=original_finger_collision_center(LOW)
  self.assertAlmostEqual(p[0],.56287,places=4)
  self.assertAlmostEqual(p[1],.24033,places=4)
  self.assertAlmostEqual(p[2],1.79133,places=4)
 def test_reject_incomplete_actual_joint_state(self):
  with self.assertRaises(ValueError):
   original_finger_collision_center({"joint2":0.1})
if __name__=="__main__":unittest.main()
