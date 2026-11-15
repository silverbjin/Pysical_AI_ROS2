#!/usr/bin/env python3
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_high_goal_precision_contract import (
 assess_precise_high_arrival,HIGH_MOVEGROUP_JOINT_CONSTRAINT_RAD,
 HIGH_ACTUAL_JOINT_MAX_ERROR_RAD)
GOAL={"joint1":.423610,"joint2":.100500,"joint3":.430060,
      "joint4":1.5707963267948966,"joint_wrist":0.0}
FAILED={"joint1":.3900264650883941,"joint2":.06922524068895992,
        "joint3":.45028819611891974,"joint4":1.5662761685661466,
        "joint_wrist":.027541191341996115}
HELD_OFFSET=(-.003151903410560264,.0005792944519445297,.018962336003945257)
class HighActualArmTDD(unittest.TestCase):
 def test_previous_movegroup_succeeded_but_34mrad_arm_error_fails(self):
  r=assess_precise_high_arrival(GOAL,FAILED,HELD_OFFSET)
  self.assertGreater(r["max_joint_error_rad"],.03)
  self.assertFalse(r["real_arm_tracking_scoped_pass"])
 def test_original_measured_joint_target_nearly_exact_is_eligible(self):
  near=dict(GOAL)
  near["joint1"]-=.001
  near["joint2"]+=.001
  near["joint3"]-=.0005
  r=assess_precise_high_arrival(GOAL,near,HELD_OFFSET)
  self.assertTrue(r["real_arm_tracking_scoped_pass"])
 def test_missing_joints_and_bad_held_offsets_fail_closed(self):
  with self.assertRaises(ValueError):
   assess_precise_high_arrival({"joint1":0},FAILED,HELD_OFFSET)
  with self.assertRaises(ValueError):
   assess_precise_high_arrival(GOAL,GOAL,(float("nan"),0.,0.))
 def test_movegroup_precision_not_relaxed_from_existing_alignment(self):
  self.assertEqual(HIGH_MOVEGROUP_JOINT_CONSTRAINT_RAD,.002)
  self.assertEqual(HIGH_ACTUAL_JOINT_MAX_ERROR_RAD,.01)
if __name__=="__main__":unittest.main()
