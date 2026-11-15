#!/usr/bin/env python3
import pathlib,math,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_jaw_axis_carry import (
 real_jaw_world_axis,real_jaw_world_axis_change,
 high_carry_jaw_compensation,MAX_ACTUAL_JAW_NORMAL_DRIFT_RAD)
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
if __name__=="__main__":unittest.main()
