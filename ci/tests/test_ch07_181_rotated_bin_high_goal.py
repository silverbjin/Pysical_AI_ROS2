"""C12 strict 5mm target and true physical obstacle yaw source contracts."""
import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_rotated_bin_high_goal import source_bin_rotated_high_goal
from ch07_181_exact_fk import original_finger_collision_center
HELD={"joint1":0.0024434445521543647,"joint2":-0.08360809946632825,
      "joint3":0.6240609326622273,"joint4":1.601339260332777,
      "joint_wrist":-0.008754126369072962}
OFFSET=[-0.0007789333929856257,0.0005550346924472305,0.017640248122233526]
ROD=[original_finger_collision_center(HELD)[k]+OFFSET[k] for k in range(3)]
SCENE={"id":"g04b_existing_gazebo_bin_collision","frame_id":"base_link",
       "center_m":[.55,.25,1.63],"box_m":[.30,.30,.20],
       "bin_yaw_rad":.35,"source":"ORIGINAL_SOLID_BIN_TEST_ONLY_YAW_ROTATED",
       "apply_planning_scene_success":True}
class TestCycle12High(unittest.TestCase):
 def test_measured_held_rod_yields_exact_5mm_with_real_collision_margin(self):
  x=source_bin_rotated_high_goal(HELD,ROD,SCENE)
  self.assertLess(x["strict_bin_xy_error_m"],.005)
  self.assertGreater(x["real_rotated_bin_sat_margin_m"],.003)
  self.assertLess(x["jaw_world_change_rad"],.25)
  self.assertLess(x["tool_axis_change_rad"],.38)
  self.assertTrue(x["requires_moveit_plan_only_before_real_motion"])
 def test_nonoriginal_shape_nonrotated_or_unheld_rod_refused(self):
  for scene,rod in (({**SCENE,"bin_yaw_rad":0.},ROD),
                    ({**SCENE,"box_m":[.28,.30,.20]},ROD),
                    ({**SCENE,"apply_planning_scene_success":False},ROD),
                    (SCENE,[ROD[0]+.2,ROD[1],ROD[2]])):
   with self.assertRaises(ValueError):
    source_bin_rotated_high_goal(HELD,rod,scene)
if __name__=="__main__":unittest.main()
