"""Focused Step1 source-bound geometry test, NO ROS/Gazebo/Action Goals."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ch07_77_step1_offline_geometry import (
    C17_ARM, C17_ROD, G04A, G04B, offline_report,
    wrist_falling_rod_sat_margin,
)


class Step1StrictGate(unittest.TestCase):
    def test_original_c17_swept_drop_aabb_has_source_level_overlap(self):
        self.assertAlmostEqual(
            wrist_falling_rod_sat_margin(C17_ARM, C17_ROD),
            -0.02968800605349, delta=1e-5)

    def test_other_fixture_not_allowed_as_real_sensor_replay(self):
        report = offline_report()
        for field in ("rod_x_m", "rod_height_m", "support_top_m",
                      "robot_spawn_z_m", "bin_yaw_rad"):
            self.assertIn(field, report["fixture_mismatches"])
            self.assertNotEqual(G04A[field], G04B[field])
        self.assertFalse(report["physics_goal_authorized"])

    def test_bounded_c17_change_cannot_be_called_collision_free(self):
        report = offline_report()
        self.assertEqual(report["bounded_sample_count"], 1570)
        self.assertLess(report["best_bounded_sample"]["sat_margin_m"], 0.)
        self.assertFalse(report["bounded_collision_free_candidate_found"])
        self.assertEqual(report["status"], "STEP1_BLOCKED")
        self.assertEqual(report["step2_e2e_l2"], "NOT_RUN")
        self.assertEqual(report["Ch10"], "HOLD")

    def test_nonfinite_input_must_not_be_passed_as_geometry(self):
        bad = list(C17_ROD)
        bad[0] = math.nan
        with self.assertRaises(ValueError):
            wrist_falling_rod_sat_margin(C17_ARM, bad)
        with self.assertRaises(ValueError):
            wrist_falling_rod_sat_margin(
                {**C17_ARM, "joint2": math.inf}, C17_ROD)


if __name__ == "__main__":
    unittest.main()
