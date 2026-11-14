#!/usr/bin/env python3
import pathlib,sys,unittest,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_post_approach_settle_contract import ARM,measured_contact_settle_target,unchanged_collision_center
class PostApproachSettle(unittest.TestCase):
 def setUp(self):
  self.actual=dict(zip(ARM,(0.,-.30,.99,math.pi/2,0.)))
 def test_requires_original_real_jointstate_not_nominal_target(self):
  self.assertEqual(measured_contact_settle_target(self.actual),self.actual)
 def test_invalid_or_unaligned_rejected(self):
  for change in [{"joint4":1.4},{"joint_wrist":.1},{"joint1":float("nan")}]:
   got=dict(self.actual);got.update(change)
   with self.assertRaises(ValueError):measured_contact_settle_target(got)
 def test_no_unmeasured_new_arm_collision_path(self):
  self.assertTrue(unchanged_collision_center((.700,0.,1.92),(.701,0.,1.92)))
  self.assertFalse(unchanged_collision_center((.700,0.,1.92),(.71,0.,1.92)))
if __name__=="__main__":unittest.main()
