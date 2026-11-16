"""Cycle09 alternate elbow numeric proof, not simulated collision PASS."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_collision_free_high_branch import alternative_high_elbow_target
from ch07_181_exact_fk import original_finger_collision_center
HELD={"joint1":-.021604442850938002,"joint2":-.06390928383311037,
      "joint3":.5760590780796367,"joint4":1.5663912464201168,
      "joint_wrist":.013581421757570503}
OFFSET=[-.008080553833572368,.001345377625129195,.019434819979277762]
ROD=[original_finger_collision_center(HELD)[i]+OFFSET[i] for i in range(3)]
HIGH=[.5119455528124157,.2280990212553216,1.96]
class TestAltHigh(unittest.TestCase):
 def test_proven_native_held_rod_fixture_and_clearance_contract(self):
  x=alternative_high_elbow_target(HELD,ROD,HIGH)
  self.assertLess(x["joint_goal"]["joint3"],-.1)
  self.assertLess(x["predicted_bin_xy_error_m"],.003)
  self.assertGreater(x["predicted_rod_xyz_m"][2],1.98)
  self.assertTrue(x["requires_moveit_plan_only_before_real_goal"])
  self.assertEqual(x["G04B"],"BLOCKED_UNTIL_NATIVE_PHYSICAL_ACCEPTANCE")
 def test_invalid_load_or_unreachable_goal_rejected(self):
  for rod,w in [([ROD[0]+.2,*ROD[1:]],HIGH),
                (ROD,[.9,.5,2.3]),
                (ROD,[float("nan"),.2,1.9])]:
   with self.assertRaises(ValueError):
    alternative_high_elbow_target(HELD,rod,w)
if __name__=="__main__":unittest.main()
