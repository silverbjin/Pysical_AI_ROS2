"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection74(unittest.TestCase):
    def test_detector_contract(self):
        src = (ROOT/'vision_basics/object_detector.py').read_text()
        ast.parse(src)
        self.assertIn("declare_parameter('min_contour_area', 500.0)", src)
        self.assertIn('if area >= self.min_contour_area:', src)
        self.assertIn("PointStamped, '/camera/target_pixel'", src)
        self.assertIn('point_msg.header = msg.header', src)
        self.assertNotIn('area > 50', src)


if __name__ == '__main__':
    unittest.main()
