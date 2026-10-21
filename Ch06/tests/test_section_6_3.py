"""Offline XML regression suite: python -m unittest discover -s Ch06/tests -p test_section_6_3.py"""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/audit_model_contract.py"
spec = importlib.util.spec_from_file_location("audit_model", p)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

URDF = '<robot name="my_robot"><link name="base_link"/></robot>'
SRDF = ('<robot name="my_robot"><group name="arm_group">'
        '<chain base_link="base_link" tip_link="link_wrist"/></group>'
        '<virtual_joint name="virtual_joint" type="fixed" '
        'parent_frame="world" child_link="base_link"/></robot>')


class RootContractTests(unittest.TestCase):
    def test_good_model(self):
        self.assertEqual(audit.check(URDF, SRDF), [])

    def test_duplicate_world(self):
        bad = URDF.replace('</robot>', '<link name="world"/></robot>')
        self.assertIn("world link inside URDF duplicates SRDF virtual root",
                      audit.check(bad, SRDF))

    def test_virtual_in_group(self):
        bad = SRDF.replace('<chain ', '<joint name="virtual_joint"/><chain ')
        self.assertTrue(any("actuated" in e for e in audit.check(URDF, bad)))

    def test_missing_virtual_joint(self):
        self.assertTrue(any("expected one SRDF virtual" in e for e in
                            audit.check(URDF, SRDF.split('<virtual_joint')[0] + '</robot>')))


if __name__ == "__main__":
    unittest.main()
