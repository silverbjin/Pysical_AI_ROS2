import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_arm_settle_contract import ARM,JOINT_GOAL_TOL_RAD,assess_arm_settle
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
if __name__=="__main__":unittest.main()
