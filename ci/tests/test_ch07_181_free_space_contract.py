#!/usr/bin/env python3
"""Pure-Python RED-regression contract. No ROS/Gazebo repeated here."""
import pathlib,sys,unittest
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_free_space_contract import (
 FINGERS,controller_sample,accept_real_finger_state)

def msg(ref=(.012,.012),feedback=(.0115,.0116),error=(.0005,.0004)):
  return SimpleNamespace(
    joint_names=list(FINGERS),
    header=SimpleNamespace(stamp=SimpleNamespace(sec=12,nanosec=0)),
    reference=SimpleNamespace(positions=list(ref)),
    feedback=SimpleNamespace(positions=list(feedback)),
    error=SimpleNamespace(positions=list(error)))

class FreeSpaceContract(unittest.TestCase):
 def test_jazzy_reference_feedback_not_legacy_desired_actual(self):
  s=controller_sample(msg())
  self.assertEqual(s["reference"]["joint_finger2"],.012)
  self.assertEqual(s["feedback"]["joint_finger2"],.0116)
  self.assertEqual(s["error"]["joint_finger2"],.0004)
 def test_action_succeeded_but_finger_frozen_must_fail(self):
  s=controller_sample(msg(feedback=(.0115,0),error=(.0005,.012)))
  verdict=accept_real_finger_state(4,0,dict(zip(FINGERS,(.0115,0))),
                                  dict.fromkeys(FINGERS,.012),[s],12,11)
  self.assertEqual(verdict,"REAL_JOINT_NOT_AT_GOAL_joint_finger2")
 def test_true_bilateral_joint_feedback_within_tolerance(self):
  s=controller_sample(msg())
  verdict=accept_real_finger_state(4,0,dict(zip(FINGERS,(.0115,.0116))),
                                  dict.fromkeys(FINGERS,.012),[s],12,11)
  self.assertEqual(verdict,"FREE_SPACE_ACTUATION_SCOPED_PASS")
 def test_missing_reference_never_passes(self):
  bad=msg();del bad.reference
  with self.assertRaisesRegex(ValueError,"REFERENCE_MISSING"):controller_sample(bad)
 def test_empty_controller_trace_never_passes(self):
  self.assertEqual(accept_real_finger_state(4,0,dict.fromkeys(FINGERS,.012),
                dict.fromkeys(FINGERS,.012),[],12,11),"CONTROLLER_TRACE_ABSENT")
 def test_wrong_joint_order_rejected(self):
  bad=msg();bad.joint_names.reverse()
  with self.assertRaisesRegex(ValueError,"JOINT_ORDER"):controller_sample(bad)
if __name__=="__main__":unittest.main()
