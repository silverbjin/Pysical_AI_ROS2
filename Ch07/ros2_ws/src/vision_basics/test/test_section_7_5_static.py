"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection75(unittest.TestCase):
    def test_transformer_and_math_syntax(self):
        for name in ('coord_transformer.py', 'projection_math.py'):
            ast.parse((ROOT/'vision_basics'/name).read_text())
        src = (ROOT/'vision_basics/coord_transformer.py').read_text()
        self.assertIn('ApproximateTimeSynchronizer(', src)
        self.assertIn('Time.from_msg(pixel.header.stamp)', src)
        self.assertIn("depth.encoding == '16UC1'", src)
        self.assertIn("depth.encoding == '32FC1'", src)
        self.assertIn('age > self.max_age', src)


if __name__ == '__main__':
    unittest.main()
