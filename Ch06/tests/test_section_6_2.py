"""Run: python -m unittest discover -s Ch06/tests -p test_section_6_2.py"""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/audit_solver_config.py"
spec = importlib.util.spec_from_file_location("ch06_solver_audit", p)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SRDF = ('<robot name="my_robot"><group name="arm_group">'
        '<joint name="joint1"/><joint name="joint2"/><joint name="joint3"/>'
        '<joint name="joint4"/><joint name="joint_wrist"/>'
        '<chain base_link="base_link" tip_link="link_wrist"/>'
        '</group></robot>')
CFG = ('arm_group:\n  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin\n'
       '  kinematics_solver_timeout: 0.05\n  position_only_ik: true\n')


class SolverConfigTests(unittest.TestCase):
    def test_valid_contract(self):
        self.assertEqual(audit.validate(CFG, SRDF), [])

    def test_missing_group(self):
        self.assertIn("missing arm_group", audit.validate(CFG.replace("arm_group:", "other:"), SRDF))

    def test_bad_timeout(self):
        self.assertIn("timeout outside teaching range",
                      audit.validate(CFG.replace("0.05", "10"), SRDF))

    def test_chain_mismatch(self):
        self.assertIn("SRDF chain endpoints mismatch",
                      audit.validate(CFG, SRDF.replace("link_wrist", "wrist_3_link")))


if __name__ == "__main__":
    unittest.main()
