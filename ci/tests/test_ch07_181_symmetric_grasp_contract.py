#!/usr/bin/env python3
"""Fail closed on wrong physical grasp goal geometry (no ROS required)."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_symmetric_grasp_contract import symmetric_close_joint_target
class SymmetricGraspContract(unittest.TestCase):
    def test_original_open_gap_and_24mm_rod_yield_bilateral_11mm(self):
        self.assertAlmostEqual(symmetric_close_joint_target(),.011)
    def test_clearance_requires_original_face_gap_not_35mm_visual_gap(self):
        self.assertAlmostEqual(symmetric_close_joint_target(.045,.024,.0005),.011)
        self.assertNotAlmostEqual(symmetric_close_joint_target(.035,.024,.0005),.011)
    def test_unphysical_geometry_rejected(self):
        for args in [(0.,.024,.0005),(.024,.024,.0005),(.045,.024,.004),(.045,.060,.0005)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                symmetric_close_joint_target(*args)
    def test_nominal_physical_contact_margin_not_tolerance_relaxation(self):
        q=symmetric_close_joint_target()
        self.assertGreater(q,(.045-.024)/2)
        self.assertLess(q,.012)
if __name__=="__main__":unittest.main()
