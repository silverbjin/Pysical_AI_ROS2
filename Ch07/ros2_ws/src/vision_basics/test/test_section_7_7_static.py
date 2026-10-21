"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection77(unittest.TestCase):
    def test_guarded_mission_contract(self):
        src = (ROOT/'vision_basics/mission_controller.py').read_text()
        ast.parse(src)
        self.assertIn("declare_parameter('enable_motion', False)", src)
        self.assertIn("'/robot/target_position'", src)
        self.assertIn('self.triggered = True', src)
        self.assertIn('self.move_arm(x, y, z + 0.15)', src)
        self.assertIn('No fresh grasp verification: STOP before lift', src)
        self.assertNotIn('lookup_transform(', src)
        self.assertNotIn('self.move_arm(1.0, 0.0,', src)


if __name__ == '__main__':
    unittest.main()
