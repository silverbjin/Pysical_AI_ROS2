#!/usr/bin/env python3
import pathlib,sys,unittest
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_hardware_native_contract import (
 relevant_introspection_pairs, explicit_command_peaks, native_link_xyz,classify_chain)
class HardwareNativeChain(unittest.TestCase):
 def test_raw_command_and_state_kept_separate(self):
  x=[SimpleNamespace(name="command_interfaces/joint_finger2/position",value=.011),
     SimpleNamespace(name="state_interfaces/joint_finger2/position",value=0.),
     SimpleNamespace(name="other",value=5.)]
  d=relevant_introspection_pairs(x)
  self.assertEqual(len(d),2)
  p=explicit_command_peaks([{"values":d}])
  self.assertEqual(max(p.values()),.011)
 def test_jtc_reference_does_not_prove_hw_command(self):
  self.assertEqual(classify_chain(.011,0,{},0),"JTC_REFERENCE_REACHED_BUT_HARDWARE_COMMAND_UNOBSERVED")
 def test_command_reached_hardware_but_native_pose_frozen(self):
  self.assertEqual(classify_chain(.011,0,{"command/joint_finger2/position":.011},0.),
                   "COMMAND_PRESENT_BUT_NATIVE_GAZEBO_JOINT_DID_NOT_MOVE")
 def test_command_not_reached_hardware_is_distinct(self):
  self.assertEqual(classify_chain(.011,0,{"command/joint_finger2/position":0.},0.),
                   "JTC_REFERENCE_TO_HARDWARE_COMMAND_GAP")
 def test_moved_native_but_state_frozen_is_distinct(self):
  self.assertEqual(classify_chain(.011,0,{"command/joint_finger2/position":.011},.011),
                   "NATIVE_LINK_MOVED_BUT_ROS_JOINTSTATE_FROZEN")
 def test_native_pose_parser_excludes_inertial_pose(self):
  raw='- Name: finger2\n  - Inertial Pose [ XYZ (m) ] [ RPY (rad) ]:\n    [0 0 0]\n  - Pose [ XYZ (m) ] [ RPY (rad) ]:\n    [0.671053 0.029066 1.89349]\n    [0 0 0]\n'
  self.assertEqual(native_link_xyz(raw,"finger2"),(.671053,.029066,1.89349))
 def test_missing_native_pose_remains_unknown(self):
  self.assertIsNone(native_link_xyz("link not found","finger2"))
if __name__=="__main__":unittest.main()
