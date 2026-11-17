"""Focused original-source single OVERHEAD candidate: hard reject before FCL."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_77_step1_single_overhead_grasp_preflight import (
    ROD_PICK_CENTER, BIN_ROD_SUPPORTED_CENTER, overhead_2r_ik,
    report_one_overhead_candidate,
)

class Original5DOFOverheadCandidate(unittest.TestCase):
    def test_initial_grasp_is_beyond_original_15m_link_reach(self):
        pick=overhead_2r_ik(ROD_PICK_CENTER)
        self.assertFalse(pick["reachable"])
        self.assertAlmostEqual(pick["shoulder_to_wrist_m"],
                               math.hypot(.70,1.44),places=10)
        self.assertGreater(pick["shoulder_to_wrist_m"],1.5)
        self.assertEqual(pick["wrist_origin_m"],[.70,0.,2.04])
        self.assertEqual(pick["ik_branches"],[])

    def test_place_goal_reaches_position_but_violates_5dof_wrist_joint(self):
        place=overhead_2r_ik(BIN_ROD_SUPPORTED_CENTER)
        self.assertTrue(place["reachable"])
        self.assertEqual(len(place["ik_branches"]),2) # two inverses, SAME pose
        pos,neg=place["ik_branches"]
        self.assertEqual((pos["elbow_branch"],neg["elbow_branch"]),
                         ("positive","negative"))
        self.assertAlmostEqual(pos["arm_goal_rad"]["joint2"],
                               -0.065256469928234,places=8)
        self.assertAlmostEqual(pos["arm_goal_rad"]["joint3"],
                               0.755542014252181,places=8)
        self.assertAlmostEqual(pos["required_wrist_rad"],
                               2.4513071092658465,places=8)
        self.assertAlmostEqual(neg["required_wrist_rad"],
                               2.9438224825473647,places=8)
        self.assertTrue(all(not b["joints_within_original_urdf_limits"]
                            for b in (pos,neg)))
        self.assertTrue(all(b["nominal_vertical_tool_down"] and
                            b["nominal_jaw_horizontal"] for b in (pos,neg)))
        self.assertTrue(all(math.dist(b["finger_world_m"],BIN_ROD_SUPPORTED_CENTER)<1e-7
                            for b in (pos,neg)))

    def test_original_solid_bin_link4_collision_reject_even_virtual_pose(self):
        place=overhead_2r_ik(BIN_ROD_SUPPORTED_CENTER)
        pos=place["ik_branches"][0]
        margin=pos["collision_preview"]["link4_bin_sat_margin_m"]
        self.assertAlmostEqual(margin,-0.0532407970822689,places=6)
        self.assertLess(margin,0.0)
        self.assertAlmostEqual(
            pos["collision_preview"]["wrist_bin_sat_margin_m"],
            0.08,places=7)
        # Wrist alone is above bin but original long link4 intersects bin.
        self.assertTrue(place["reachable"])

    def test_fail_closed_no_moveit_goal_no_motor_no_global_claim(self):
        r=report_one_overhead_candidate()
        self.assertFalse(r["pickup_position_reachable"])
        self.assertFalse(r["supported_place_within_joint_limits"])
        self.assertFalse(r["supported_place_source_collision_clear"])
        self.assertEqual(r["candidate_status"],"REJECTED_PRE_FCL_HARD_GEOMETRY")
        self.assertEqual(r["moveit_fcl_plan_only"],
                         "NOT_REQUESTED_PRE_FCL_HARD_REJECT")
        self.assertEqual(r["moveit_plan_only_goals_sent"],0)
        self.assertEqual(r["motor_goals_sent"],0)
        self.assertEqual(r["status"],"STEP1_BLOCKED")
        self.assertEqual(r["G04B_PHYSICAL_CLEAN"],"BLOCKED")
        self.assertEqual(r["CH07_77_E2E"],"BLOCKED")
        self.assertEqual(r["Ch10"],"HOLD")
        self.assertIn("arbitrary orientations or alternative regrasp",
                      r["not_proven"])

    def test_nonfinite_geometry_is_not_promoted(self):
        for bad in (
            (math.nan,0.,1.94), (0.7,math.inf,1.94),
            (0.7,0.,float("-inf"))
        ):
            with self.assertRaises(ValueError):
                overhead_2r_ik(bad)

if __name__=="__main__":
    unittest.main()
