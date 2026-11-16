"""Cycle13: measured-offset adaptive high-goal, original strict gates."""
import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_rotated_bin_high_goal import source_bin_rotated_high_goal
from ch07_181_exact_fk import original_finger_collision_center
HELD={"joint1":0.0024434445521543647,"joint2":-0.08360809946632825,
      "joint3":0.6240609326622273,"joint4":1.601339260332777,
      "joint_wrist":-0.008754126369072962}
HISTORICAL_OFFSET=[-0.0007789333929856257,0.0005550346924472305,0.017640248122233526]
# Cycle12 physically observed offset (not the same held-arm sample).
C12_L2_OBSERVED_OFFSET=[-0.00580180,0.00094007,0.01868464]
C13_LAST_LIFT_ARM={"joint1":-0.03270249803258013,
      "joint2":-0.08987911463701247,
      "joint3":0.5735325131612498,
      "joint4":1.5482159287412602,
      "joint_wrist":-0.0069640212233951235}
# C13 original raw held-world object offset; lift arm is a *prior*
# snapshot, not an invented claim about the exact hold-time JointState.
C13_REAL_HELD_OFFSET=[-0.001135262342006449,0.001124849022535129,
                      0.016879870544068254]
SCENE={"id":"g04b_existing_gazebo_bin_collision","frame_id":"base_link",
       "center_m":[.55,.25,1.63],"box_m":[.30,.30,.20],
       "bin_yaw_rad":.35,"source":"ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED",
       "apply_planning_scene_success":True}

def rod_for(offset):
    c=original_finger_collision_center(HELD)
    return [c[k]+offset[k] for k in range(3)]

class TestCycle13High(unittest.TestCase):
 def test_c13_original_lift_orientation_and_raw_held_offset_preflight(self):
  # C13 could not find any q4 in old [1.42,1.48] while preserving
  # native jaw. This protects against a repeat of the same frozen seed.
  center=original_finger_collision_center(C13_LAST_LIFT_ARM)
  rod=[center[k]+C13_REAL_HELD_OFFSET[k] for k in range(3)]
  x=source_bin_rotated_high_goal(C13_LAST_LIFT_ARM,rod,SCENE)
  self.assertLess(x["strict_bin_xy_error_m"],.005)
  self.assertGreater(x["real_rotated_bin_sat_margin_m"],.003)
  self.assertLess(x["jaw_world_change_rad"],.25)
  self.assertLess(x["tool_axis_change_rad"],.38)
  self.assertLess(x["joint_goal"]["joint4"],1.42)
  self.assertTrue(x["requires_moveit_plan_only_before_real_motion"])

 def test_original_and_new_native_offsets_use_unaltered_strict_contract(self):
  for off in (HISTORICAL_OFFSET,C12_L2_OBSERVED_OFFSET):
   with self.subTest(offset=off):
    x=source_bin_rotated_high_goal(HELD,rod_for(off),SCENE)
    self.assertLess(x["strict_bin_xy_error_m"],.005)
    self.assertGreaterEqual(x["real_rotated_bin_sat_margin_m"],.003)
    self.assertLess(x["jaw_world_change_rad"],.25)
    self.assertLess(x["tool_axis_change_rad"],.38)
    self.assertGreater(x["predicted_rod_xyz_m"][2],1.98)
    self.assertGreater(x["bounded_candidates_checked"],0)
    self.assertTrue(x["requires_moveit_plan_only_before_real_motion"])
    self.assertEqual(x["G04B"],"BLOCKED_UNTIL_NATIVE_CONTACT_RELEASE_ROI_PASS")
 def test_original_bin_dimensions_and_rotated_quaternion_are_not_relaxed(self):
  for change in ({"bin_yaw_rad":0.},
                 {"box_m":[.28,.30,.20]},
                 {"center_m":[.55,.25,1.60]},
                 {"apply_planning_scene_success":False},
                 {"source":"ORIGINAL_STATIC_GAZEBO_BIN"}):
   with self.assertRaises(ValueError):
    source_bin_rotated_high_goal(HELD,rod_for(HISTORICAL_OFFSET),
                                  {**SCENE,**change})
 def test_invalid_held_joint_nan_rod_and_not_held_fails_closed(self):
  for arm,rod in ((HELD,[math.nan,0,0]),
                  (HELD,[0,0,0]),
                  ({**HELD,"joint1":math.nan},rod_for(HISTORICAL_OFFSET)),
                  ({"joint1":.0},rod_for(HISTORICAL_OFFSET))):
   with self.assertRaises(ValueError):
    source_bin_rotated_high_goal(arm,rod,SCENE)
if __name__=="__main__":
 unittest.main()
