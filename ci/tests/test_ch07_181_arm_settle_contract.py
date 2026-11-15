import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_arm_settle_contract import ARM,JOINT_GOAL_TOL_RAD,assess_arm_settle,lower_bin_settle_recovery_eligible,MOVEGROUP_FEEDBACK_MAX_ERROR_RAD,LOWER_SETTLE_RECOVERY_MAX_INITIAL_ERROR_RAD
class ArmSettleTest(unittest.TestCase):
 def setUp(self):self.target=dict(zip(ARM,(0.,-.2961288,.9853157,1.5707963,0.)))
 def test_tolerance_not_relaxed(self):
  self.assertEqual(JOINT_GOAL_TOL_RAD,.01)
  self.assertLess(JOINT_GOAL_TOL_RAD,.025)
 def test_succeeded_action_but_real_q4_error_fails(self):
  actual=dict(self.target);actual["joint4"]-=.028
  self.assertEqual(assess_arm_settle(4,0,self.target,actual)[0],"ARM_SETTLE_ACTUAL_JOINTS_FAILED")
 def test_actual_measured_five_joints_pass(self):
  actual={n:v+.0004 for n,v in self.target.items()}
  self.assertEqual(assess_arm_settle(4,0,self.target,actual)[0],"ARM_SETTLE_SCOPED_PASS")
 def test_aborted_or_missing_never_pass(self):
  self.assertNotEqual(assess_arm_settle(6,-5,self.target,self.target)[0],"ARM_SETTLE_SCOPED_PASS")
  self.assertNotEqual(assess_arm_settle(4,0,self.target,dict(list(self.target.items())[:-1]))[0],"ARM_SETTLE_SCOPED_PASS")
class LowerBinFJTRecoveryTDD(unittest.TestCase):
 def test_only_actual_reproduced_joint3_gap_eligible(self):
  e={n:.002 for n in ARM};e["joint3"]=.13486462231863716
  self.assertTrue(lower_bin_settle_recovery_eligible("lower_into_bin",e))
  self.assertFalse(lower_bin_settle_recovery_eligible("pregrasp",e))
  self.assertFalse(lower_bin_settle_recovery_eligible("transfer_high_above_bin",e))
 def test_abnormally_large_or_nonfinite_error_stops_before_new_goal(self):
  e={n:.002 for n in ARM}
  for bad in (.20,float("nan"),float("inf"),-.1):
   e["joint3"]=bad
   self.assertFalse(lower_bin_settle_recovery_eligible("lower_into_bin",e))
 def test_no_additional_fjt_when_already_within_existing_window(self):
  e={n:.001 for n in ARM}
  self.assertFalse(lower_bin_settle_recovery_eligible("lower_into_bin",e))
 def test_strict_final_fjt_never_relaxed(self):
  self.assertEqual(JOINT_GOAL_TOL_RAD,.01)
  self.assertEqual(MOVEGROUP_FEEDBACK_MAX_ERROR_RAD,.075)
  self.assertEqual(LOWER_SETTLE_RECOVERY_MAX_INITIAL_ERROR_RAD,.18)
  e=dict(zip(ARM,(0.,-.4,1.25,1.57,0.)))
  m=dict(e,joint3=e["joint3"]-.015)
  self.assertNotEqual(assess_arm_settle(4,0,e,m)[0],"ARM_SETTLE_SCOPED_PASS")
 def test_missing_joint_names_fail_closed(self):
  e={n:.001 for n in ARM};del e["joint3"]
  self.assertFalse(lower_bin_settle_recovery_eligible("lower_into_bin",e))
if __name__=="__main__":unittest.main()
