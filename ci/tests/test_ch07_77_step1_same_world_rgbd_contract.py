"""No-ROS L0: SAME G04B physical 80mm world + camera RGBD admission contract."""
import ast
from pathlib import Path
import math
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"ci"))
from ch07_77_g04b_physics_fixture import build as physical_build
from ch07_181_bin_yaw_single_factor import rotate_bin

class TestSingleWorldRGBD(unittest.TestCase):
    def test_80mm_native_grasp_world_is_exact_source_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"physical.sdf"
            receipt=Path(td)/"physical.json"
            physical_build(
                ROOT/"ci/docker/fixtures/ch07_77_g02_dynamic_red_world.sdf",
                out,receipt)
            data=__import__("json").loads(receipt.read_text())
            self.assertFalse(data["rod_static"])
            self.assertEqual(data["rod_center_initial_world_m"],[.70,0,1.94])
            self.assertEqual(data["height_m"],.08)
            self.assertEqual(data["radius_m"],.012)
            root=ET.parse(out).getroot()
            world=root.find("./world[@name='book_camera']")
            self.assertEqual(world.findtext("./plugin[@name='gz::sim::systems::Sensors']/render_engine"),"ogre2")
            rod=world.find("./model[@name='g04_grasp_cylinder']")
            self.assertEqual(rod.findtext("static"),"false")
            self.assertEqual(rod.findtext(".//geometry/cylinder/length"),"0.08")
            self.assertEqual(rod.findtext("./link/inertial/mass"),"0.05")
            self.assertEqual(world.find("./model[@name='g04_support']").findtext("pose").split()[:3],[".70","0","1.897"])
            yaw=rotate_bin(out,Path(td)/"yaw.json")
            self.assertEqual(yaw["only_change"],"real_bin_model_yaw_0_to_0.35_rad")
            self.assertEqual(yaw["bin_world_center_m"],[.55,.25,1.63])

    def test_runner_does_not_mix_original_240mm_sensor_target(self):
        source=(ROOT/"ci/ch07_77_step1_same_world_rgbd_once.sh").read_text()
        self.assertIn("ch07_77_g04b_physics_fixture.py",source)
        self.assertNotIn('python3 "$ROOT/ci/ch07_77_g04a_graspable_fixture.py"',source)
        self.assertIn("ch07_181_fixed_world_base_anchor.py",source)
        self.assertIn(' -z 0.0 ',source)
        # Sensor-only run uses exact source 7-joint URDF bounds. A future
        # actual motor L2 must pin the proven physical DART profile separately.
        self.assertIn("DART_TEST_ONLY_1MM_LIMIT_MARGIN_NOT_APPLIED_NO_MOTOR_GOALS",source)
        self.assertNotIn('python3 "$ROOT/ci/ch07_181_g04b_dart_limit_margin.py"',source)
        self.assertIn("CH07_77_G04B_SHORT_LIVE=YES",source)
        self.assertIn("original_real_sensor",source.replace("ORIGINAL_ROS_DETECTOR_COORD_TRANSFORM_NO_GOALS","original_real_sensor") )

    def test_source_sensor_target_not_native_pose_for_goal(self):
        source=(ROOT/"ci/ch07_77_step1_same_world_rgbd_once.sh").read_text()
        self.assertIn("mission_controller",source)
        self.assertIn("object_detector",source)
        self.assertIn("coord_transformer",source)
        self.assertNotIn('mode:=execute_sim',source)
        self.assertNotIn('FollowJointTrajectory.Goal',source)
        self.assertNotIn('mission_plan_only',source)
        self.assertNotIn('set_pose',source.lower())
        self.assertNotIn('attach_object',source.lower())

    def test_existing_accepted_g04a_witness_scope_is_unchanged_by_default(self):
        source=(ROOT/"ci/ch07_77_g04a_live_small_target_witness.py").read_text()
        self.assertIn('short_live=os.environ.get("CH07_77_G04B_SHORT_LIVE","NO")=="YES"',source)
        self.assertIn('(.665,.71) if short_live else (.765,.81)',source)
        self.assertIn('CH07_77_G04A_REAL_OGRE2_RGBD_RED_DETECTOR_3D_TARGET_NO_GOAL_SCOPED_PASS',source)

    def test_coord_log_exact_timestamp_pattern(self):
        runner=(ROOT/"ci/ch07_77_step1_same_world_rgbd_once.sh").read_text()
        expr=next(x.partition("=")[2] for x in runner.splitlines()
                  if x.startswith('pat=r"CH07_75_VALID_3D_TARGET'))
        regex=ast.literal_eval(expr)
        test="CH07_75_VALID_3D_TARGET stamp=17.755 xyz=(0.688066,0.001349,1.942992)"
        result=re.search(regex,test)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(float(result.group(2)),.688066)

if __name__=="__main__":
    unittest.main()
