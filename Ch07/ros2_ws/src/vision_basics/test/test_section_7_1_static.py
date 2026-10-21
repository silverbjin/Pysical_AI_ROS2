"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection71(unittest.TestCase):
    def test_setup_and_dependencies(self):
        src = (ROOT / 'setup.py').read_text()
        ast.parse(src)
        xml = ET.parse(ROOT / 'package.xml').getroot()
        names = {x.text for x in xml.findall('exec_depend')}
        for name in ('rclpy', 'sensor_msgs', 'cv_bridge', 'geometry_msgs',
                     'control_msgs', 'trajectory_msgs', 'moveit_msgs'):
            self.assertIn(name, names)
        for entry in ('simple_image_subscriber', 'vision_processor',
                      'object_detector', 'gripper_controller', 'mission_controller'):
            self.assertIn(f"'{entry} = vision_basics.{entry}:main'", src)


if __name__ == '__main__':
    unittest.main()
