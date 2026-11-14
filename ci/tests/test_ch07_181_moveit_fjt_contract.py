#!/usr/bin/env python3
import pathlib,sys,unittest
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_moveit_fjt_contract import ARM,DIRECT_FJT_ARM_GOAL_TOLERANCE_RAD,validate_moveit_plan_for_direct_fjt
def make(points=((0.,0.,0.,0.,0.),(.1,.2,.3,.4,.5)),ts=(0.,2.)):
 rows=[SimpleNamespace(positions=list(q),time_from_start=SimpleNamespace(sec=int(t),nanosec=int((t-int(t))*1e9)))
       for q,t in zip(points,ts)]
 return SimpleNamespace(joint_names=list(ARM),points=rows)
class MoveItPlanToFJT(unittest.TestCase):
 def setUp(self):self.target=dict(zip(ARM,(.1,.2,.3,.4,.5)))
 def test_valid_real_plan_required_before_direct_control(self):
  x=validate_moveit_plan_for_direct_fjt(make(),self.target)
  self.assertEqual(x["planned_points"],2)
  self.assertEqual(x["duration_s"],2.)
 def test_joint_name_mismatch_never_executes(self):
  a=make();a.joint_names[-1]="wrong"
  with self.assertRaisesRegex(ValueError,"NAMES_INVALID"):validate_moveit_plan_for_direct_fjt(a,self.target)
 def test_stale_or_nonfinite_or_zero_time_rejected(self):
  for a in (make(ts=(0.,0.)),make(points=((0.,0.,0.,0.,0.),(.1,float("nan"),.3,.4,.5)))):
   with self.assertRaises(ValueError):validate_moveit_plan_for_direct_fjt(a,self.target)
 def test_goal_position_residual_not_relaxed(self):
  self.assertEqual(DIRECT_FJT_ARM_GOAL_TOLERANCE_RAD,.035)
  a=make(points=((0.,0.,0.,0.,0.),(.1,.2,.3,.4,.54)))
  with self.assertRaisesRegex(ValueError,"END_NOT_AT_GOAL"):validate_moveit_plan_for_direct_fjt(a,self.target)
if __name__=="__main__":unittest.main()
