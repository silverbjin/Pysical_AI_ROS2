"""Official staged Place/Open/Retreat baseline meets native C17 source? No motor."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_77_step1_supported_release_preflight import (
    source_support_before_open,source_native_rod_half_height)

class SupportedPlaceC17Preflight(unittest.TestCase):
    def test_real_rod_quaternion_vertical_extent(self):
        self.assertAlmostEqual(source_native_rod_half_height(),.0417378193,
                               delta=2e-6)

    def test_true_original_C17_vertical_support_is_obstructed(self):
        r=source_support_before_open()
        self.assertEqual(r["baseline"],"MOVEIT_OFFICIAL_PLACE_OPEN_RETREAT_STAGE_ORDER")
        self.assertAlmostEqual(r["rod_bottom_above_bin_top_m"],.1432498353,
                               delta=1e-5)
        self.assertAlmostEqual(r["first_wrist_bin_collision_downward_m"],.0658,
                               delta=0.0002)
        self.assertGreater(r["unachieved_placement_downward_m"],.075)
        self.assertFalse(r["supported_place_by_C17_vertical_drop_feasible"])

    def test_unverified_side_candidate_never_authorizes_motor(self):
        r=source_support_before_open()
        self.assertEqual(r["status"],"STEP1_BLOCKED")
        self.assertFalse(r["physical_goal_authorized"])
        self.assertEqual(r["candidate_status"],"HYPOTHESIS_UNVERIFIED_NOT_EXECUTABLE")
        self.assertEqual(r["E2E"],"BLOCKED")
        self.assertIn("real_support_contact_before_gripper_open",r["requires"])

if __name__=="__main__":
    unittest.main()
