"""Source-based necessary-condition test, no fake physics or ROS imports."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ch07_77_step1_side_outside_no_go import side_outside_necessary_condition
from ch07_77_step1_offline_geometry import C17_ARM, C17_ROD


class SideOutsideC17Bound(unittest.TestCase):
    def test_native_wrist_rod_distance_and_fixed_grip_invariant(self):
        result = side_outside_necessary_condition()
        self.assertAlmostEqual(
            result["native_rod_to_wrist_box_center_distance_m"],
            0.08434057346593132, delta=1e-7)
        self.assertAlmostEqual(
            result["max_wrist_center_distance_from_bin_m"],
            0.17434057346593132, delta=1e-7)

    def test_outside_xy_requires_180mm_but_only_174mm_available(self):
        result = side_outside_necessary_condition()
        self.assertAlmostEqual(
            result["necessary_wrist_footprint_separation_distance_m"],
            0.18, delta=1e-10)
        self.assertAlmostEqual(
            result["minimum_unachievable_horizontal_separation_m"],
            0.005659426534068673, delta=1e-7)
        self.assertFalse(result["fixed_native_grip_outside_xy_feasible"])
        self.assertEqual(
            result["candidate_status"],
            "REJECT_FIXED_C17_GRIP_WRIST_OUTSIDE_BIN_XY")

    def test_scope_never_authorizes_motor_or_global_impossibility(self):
        result = side_outside_necessary_condition()
        self.assertFalse(result["physical_goal_authorized"])
        self.assertEqual(result["status"], "STEP1_BLOCKED")
        self.assertEqual(result["step2_motor_e2e"], "NOT_RUN")
        self.assertIn(
            "3D collision-free pose with wrist completely ABOVE bin",
            result["not_proven"])

    def test_invalid_source_rejected_before_geometry(self):
        for replacement in (
            {**C17_ARM, "joint2": float("nan")},
            {**C17_ARM, "joint3": float("inf")},
            {**C17_ARM, "fake_joint": 0.0},
        ):
            with self.assertRaises(ValueError):
                side_outside_necessary_condition(arm=replacement)
        with self.assertRaises(ValueError):
            side_outside_necessary_condition(
                rod=(C17_ROD[0], math.nan, C17_ROD[2]))


if __name__ == "__main__":
    unittest.main()
