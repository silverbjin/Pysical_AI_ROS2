"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection73(unittest.TestCase):
    def test_processor_contract(self):
        src = (ROOT/'vision_basics/vision_processor.py').read_text()
        ast.parse(src)
        self.assertIn("declare_parameter('show_gui', False)", src)
        self.assertIn('if self.show_gui:', src)
        self.assertIn('except cv2.error', src)
        self.assertIn('processed_msg.header = msg.header', src)
        self.assertIn('encoding="mono8"', src)


if __name__ == '__main__':
    unittest.main()
