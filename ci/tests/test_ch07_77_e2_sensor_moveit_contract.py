"""E1/E2 focused no-ROS tests: real target lineage into plan-only IK joints."""
from pathlib import Path
import ast
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "Ch07/ros2_ws/src/vision_basics"
sys.path.insert(0, str(PKG))
from vision_basics.mission_geometry import (ARM, FixtureCalibration,
    arm_ik_fixture, fixture_plan_targets, physical_short_rod_profile)


class TestE2RealSensorPlanContract(unittest.TestCase):
    def test_finite_sensor_target_generates_three_ordered_5dof_targets(self):
        stages = fixture_plan_targets((0.78, 0.0, 1.94))
        self.assertEqual([t["stage"] for t in stages],
                         ["pregrasp", "approach", "grasp"])
        self.assertEqual(tuple(round(v, 2) for v in stages[0]["wrist_xyz_m"]),
                         (0.49, 0.0, 1.85))
        self.assertEqual(tuple(round(v, 2) for v in stages[-1]["wrist_xyz_m"]),
                         (0.63, 0.0, 1.85))
        for s in stages:
            self.assertEqual(tuple(s["joints_rad"]), ARM)
            self.assertTrue(all(math.isfinite(q)
                                for q in s["joints_rad"].values()))

    def test_a_different_real_sensor_target_changes_joint_goals(self):
        a = fixture_plan_targets((0.78, 0.0, 1.94))
        b = fixture_plan_targets((0.82, 0.04, 1.95))
        self.assertNotEqual(a[0]["joints_rad"], b[0]["joints_rad"])
        self.assertNotEqual(a[-1]["wrist_xyz_m"], b[-1]["wrist_xyz_m"])

    def test_native_80mm_same_world_real_sensor_calibration_is_distinct(self):
        # Actual G04B short-rod Run 43984345894, real RGBD stamp 16.204.
        live=(0.6880574607854186, 0.0011689712676005552,
              1.9436128275772655)
        with self.assertRaises(ValueError):
            fixture_plan_targets(live)  # NEVER silently use legacy G04A!
        profile=physical_short_rod_profile()
        self.assertEqual(profile.source_id,"g04b_80mm_red_rod_test_only")
        stages=fixture_plan_targets(live,profile)
        self.assertEqual([v["stage"] for v in stages],
                         ["pregrasp","approach","grasp"])
        self.assertAlmostEqual(stages[0]["wrist_xyz_m"][0],0.49,delta=1e-9)
        self.assertAlmostEqual(stages[1]["wrist_xyz_m"][0],0.56,delta=1e-9)
        self.assertAlmostEqual(stages[2]["wrist_xyz_m"][0],0.63,delta=1e-9)
        self.assertAlmostEqual(stages[2]["wrist_xyz_m"][2],1.85,delta=1e-9)
        self.assertEqual(len(stages[-1]["joints_rad"]),5)
        with self.assertRaises(ValueError):
            fixture_plan_targets((0.788,0,1.94),profile)

    def test_invalid_sensor_targets_fail_without_plan(self):
        bad = [(float("nan"), 0, 1.94), (float("inf"), 0, 1.94),
               (0.1, 0, 1.94), (0.78, 1.0, 1.94),
               (0.78, 0, -1), (0.78, 0), ("0.78", 0, 1.94)]
        for xyz in bad:
            with self.subTest(xyz=xyz):
                with self.assertRaises(ValueError):
                    fixture_plan_targets(xyz)

    def test_unapproved_fixture_or_calibration_fail_closed(self):
        with self.assertRaises(ValueError):
            fixture_plan_targets((0.78, 0, 1.94),
                                 FixtureCalibration(source_id="other"))
        with self.assertRaises(ValueError):
            fixture_plan_targets((0.78, 0, 1.94),
                                 FixtureCalibration(approach_distance_m=0.4))
        with self.assertRaises(ValueError):
            fixture_plan_targets((0.78, 0, 1.94),
                                 FixtureCalibration(visible_surface_to_wrist_z_m=float("nan")))

    def test_ik_rejects_unreachable(self):
        with self.assertRaises(ValueError):
            arm_ik_fixture(2.0, 0, 5.0)

    def test_runtime_mode_defaults_no_goal_and_only_plan_only_is_supported(self):
        path = PKG / "vision_basics/mission_plan_only.py"
        source = path.read_text()
        tree = ast.parse(source)
        self.assertIn('ALLOWED_MODES = ("observe", "plan_only")', source)
        self.assertIn("goal.planning_options.plan_only = True", source)
        self.assertNotIn("FollowJointTrajectory", "\n".join(
            line for line in source.splitlines() if line.startswith("from ")))
        self.assertNotIn("execute_sim", str([
            x.value for x in ast.walk(tree) if isinstance(x, ast.Constant)
            and isinstance(x.value, str) and x.value in ("execute_sim",)]))
        self.assertIn("/ch07_77/target_ready", source)


if __name__ == "__main__":
    unittest.main()
