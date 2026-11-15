#!/usr/bin/env python3
"""Fail-closed raw high-stage audit, no Gazebo imports."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_high_joint2_native_audit import inspect
def receipt():
 return {"last_high_joint2_causal_even_on_failure":{
   "start_sim_s":56.,"end_sim_s":61.,
   "jtc_reference_feedback_error":[{"stamp":57.,"reference_joint2_rad":.105,"feedback_joint2_rad":.090},
                                    {"stamp":60.,"reference_joint2_rad":.105,"feedback_joint2_rad":.093}],
   "hardware_command_position":[{"stamp":59.,"name":"command_interface.joint2/position","position_rad":.105}],
   "observer_errors":[]}}
def row(t,phase,cmd,pos,name="joint2"):
 return {"sim_time_s":str(t),"phase":phase,"joint_name":name,
         "velocity_cmd_mps":str(cmd),"position_m":str(pos)}
class TestReadOnlyHighBoundary(unittest.TestCase):
 def test_nonzero_cmd_frozen_is_blocked(self):
  x=inspect(receipt(),[row(59.,"pre",.02,.093),row(60.,"post",.02,.093)])
  self.assertEqual(x["verdict"],"HIGH_JOINT2_NONZERO_NATIVE_CMD_BUT_FROZEN")
  self.assertEqual(x["G04B"],"BLOCKED")
 def test_missing_source_evidence_is_unknown(self):
  self.assertEqual(inspect({},[])["verdict"],"HIGH_MOVEGROUP_CAUSAL_WINDOW_MISSING")
  x=inspect(receipt(),[])
  self.assertEqual(x["verdict"],"NATIVE_PRE_PHYSICS_COMMAND_UNOBSERVED")
 def test_missing_hardware_not_zero(self):
  p=receipt();p["last_high_joint2_causal_even_on_failure"]["hardware_command_position"]=[]
  self.assertEqual(inspect(p,[row(58.,"pre",.02,.093)])["verdict"],"HARDWARE_COMMAND_UNOBSERVED")
 def test_motion_is_not_grasp_pass(self):
  x=inspect(receipt(),[row(59.,"pre",.02,.09),row(60.,"post",.02,.11)])
  self.assertEqual(x["verdict"],"HIGH_JOINT2_NATIVE_MOTION_PRESENT_CHECK_TRACKING_AND_CONSTRAINT")
  self.assertEqual(x["G04B"],"BLOCKED")
 def test_out_of_window_and_fingers_ignored(self):
  x=inspect(receipt(),[row(59.,"pre",.02,.093,"joint_finger1"),row(90.,"pre",.02,.093)])
  self.assertEqual(x["verdict"],"NATIVE_PRE_PHYSICS_COMMAND_UNOBSERVED")
if __name__=="__main__":unittest.main()
