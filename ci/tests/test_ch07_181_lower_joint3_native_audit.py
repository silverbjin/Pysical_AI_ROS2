#!/usr/bin/env python3
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_lower_joint3_native_audit import inspect,inspect_window
def mk_window():
 return {"start_sim_s":69.,"end_sim_s":75.,
         "goal_joint3_rad":1.25484,"actual_joint3_rad":1.12860,
         "jtc_reference_feedback_error":[{"stamp":69+i*.03,
               "reference_joint3_rad":1.25484,"feedback_joint3_rad":1.1286}
               for i in range(200)],
         "hardware_command_position":[{"stamp":69+i*.03,
               "name":"command_interface.joint3/position","position_rad":1.25484}
               for i in range(200)]}
def mk_rows(moving=False):
 rows=[]
 for i in range(200):
  t=69+i*.03
  pos=1.1+(i*.0008 if moving else .0000001*i)
  rows.append({"joint_name":"joint3","phase":"pre",
               "sim_time_s":str(t),"velocity_cmd_mps":".125",
               "velocity_mps":".04" if moving else ".00012",
               "position_m":str(pos)})
 return rows
class T(unittest.TestCase):
 def test_stall_with_nonzero_velocity_cmd(self):
  o=inspect_window(mk_window(),mk_rows())
  self.assertEqual(o["verdict"],"LOWER_JOINT3_NATIVE_STALL_WITH_NONZERO_COMMAND")
  self.assertGreater(o["measurements"]["actual_goal_error_rad"],.12)
 def test_real_motion_is_not_falsely_a_stall(self):
  self.assertEqual(inspect_window(mk_window(),mk_rows(moving=True))["verdict"],
      "LOWER_JOINT3_COMMAND_AND_MOTION_PRESENT_REVIEW_CONSTRAINT")
 def test_limiter_flag_is_not_a_hw_command(self):
  w=mk_window()
  w["hardware_command_position"]=[{"stamp":69+i*.03,
    "name":"command_interface.joint3/position.is_limited","position_rad":0} for i in range(200)]
  self.assertEqual(inspect_window(w,mk_rows())["verdict"],
                   "HARDWARE_POSITION_COMMAND_MISSING")
 def test_incomplete_joint3_cannot_claim_stall(self):
  self.assertEqual(inspect_window(mk_window(),[])["verdict"],
                   "NATIVE_ECS_COMMAND_OR_POSITION_MISSING")
 def test_only_same_goal_strict_fjt_is_joined(self):
  w=mk_window()
  receipt={"last_lower_joint3_causal_even_on_failure":w,
    "last_arm_settle_even_on_failure":{"desired":{"joint3":0.95},
        "joint3_observation_window":mk_window()}}
  o=inspect(receipt,mk_rows())
  self.assertEqual(o["strict_fjt"]["verdict"],"NOT_RUN_OR_DIFFERENT_GOAL")
  self.assertEqual(o["G04B"],"BLOCKED")
if __name__=="__main__":unittest.main()
