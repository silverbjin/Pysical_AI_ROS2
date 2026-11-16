#!/usr/bin/env python3
import pathlib,math,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_jaw_axis_carry import (
 real_jaw_world_axis,real_jaw_world_axis_change,
 high_carry_jaw_compensation,MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD,
 exact_world_jaw_lower_plan)
from ch07_181_exact_fk import original_finger_collision_center
HELD={"joint1":.018258045521515182,"joint2":-.048328939890137694,
 "joint3":.6214992296231209,"joint4":1.5986430066757167,
 "joint_wrist":.02452944547108134}
HIGH={"joint1":.42461607273068674,"joint2":.0975863377651166,
 "joint3":.43326004944058416,"joint4":math.pi/2,"joint_wrist":0.0}
class JawAxisCarryTDD(unittest.TestCase):
 def test_raw_high_yaw_rotates_jaw_37centiradian_and_causes_slip_risk(self):
  self.assertGreater(real_jaw_world_axis_change(HELD,HIGH),.36)
 def test_one_real_q4_compensates_world_jaw_normal_not_wrist_xyz(self):
  z=high_carry_jaw_compensation(HELD,HIGH)
  self.assertAlmostEqual(z["target"]["joint4"],1.24562,places=3)
  self.assertGreater(z["original_predicted_jaw_change_rad"],.36)
  self.assertLess(z["compensated_predicted_jaw_change_rad"],.20)
  self.assertLess(z["compensated_predicted_jaw_change_rad"],MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD)
  self.assertLess(math.dist(original_finger_collision_center(HIGH),
      original_finger_collision_center(z["target"])),1e-8)
 def test_original_urdf_jaw_axis_at_q4_pi_over_two_along_world_y(self):
  a=dict(HELD,joint1=0.,joint2=0.,joint3=0.,joint4=math.pi/2,joint_wrist=0.)
  v=real_jaw_world_axis(a)
  self.assertAlmostEqual(v[0],0.,places=7)
  self.assertAlmostEqual(v[1],1.,places=7)
  self.assertAlmostEqual(v[2],0.,places=7)
 def test_invalid_or_unbounded_rotation_fails_closed(self):
  with self.assertRaises(ValueError):
   high_carry_jaw_compensation(HELD,dict(HIGH,joint4=0.))
  with self.assertRaises(ValueError):
   high_carry_jaw_compensation(dict(HELD,joint1=float("nan")),HIGH)
  with self.assertRaises(ValueError):
   high_carry_jaw_compensation(HELD,dict(HIGH,joint_wrist=.1))
class ExactWorldLowerTDD(unittest.TestCase):
 def setUp(self):
  self.high={"joint1":.4213824126806682,"joint2":.08382393430447412,
             "joint3":.439455530265983,"joint4":1.2359596400293964,
             "joint_wrist":-.001588469730200483}
  self.lower={"joint1":.42489200938092025,"joint2":-.40562362175686745,
              "joint3":1.254839883790849,"joint4":math.pi/2,"joint_wrist":0.}
  self.offset=[-.00040626510217800504,.0009670075595501586,
               .01741101185278149]
 def test_true_world_jaw_and_tool_orientation_improves_with_same_q3(self):
  r=exact_world_jaw_lower_plan(self.high,self.lower,self.offset)
  self.assertLess(r["jaw_world_change_rad"],1e-5)
  self.assertGreater(r["historical_jaw_world_change_rad"],.30)
  self.assertLess(r["tool_world_change_rad"],r["historical_tool_world_change_rad"])
  self.assertEqual(r["target"]["joint2"],self.lower["joint2"])
  self.assertEqual(r["target"]["joint3"],self.lower["joint3"])
  self.assertLess(r["predicted_bin_xy_error_m"],.06)
  self.assertEqual(r["scope"],"KINEMATIC_ONLY_NOT_PHYSICAL_PASS")
 def test_missing_nonfinite_or_unheld_object_blocks_goals(self):
  for h,l,o in [({"joint1":0.},self.lower,self.offset),
                (self.high,dict(self.lower,joint3=float("nan")),self.offset),
                (self.high,self.lower,[float("nan"),0.,0.]),
                (self.high,self.lower,[.25,.25,.25])]:
   with self.assertRaises(ValueError):
    exact_world_jaw_lower_plan(h,l,o)
if __name__=="__main__":unittest.main()
