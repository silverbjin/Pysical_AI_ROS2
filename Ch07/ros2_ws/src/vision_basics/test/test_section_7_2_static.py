"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection72(unittest.TestCase):
    def test_xml_and_launch(self):
        camera = ET.parse(ROOT / 'urdf/camera.xacro').getroot()
        ET.parse(ROOT / 'urdf/my_robot.urdf.xacro')
        world = ET.parse(ROOT / 'worlds/ch07_camera_lab.sdf').getroot()
        self.assertIsNotNone(camera.find(".//*[@name='camera_optical_frame']"))
        self.assertIsNotNone(camera.find(".//*[@type='rgbd_camera']"))
        self.assertIn('camera.xacro', (ROOT/'urdf/my_robot.urdf.xacro').read_text())
        self.assertIn('gz-sim-sensors-system', ET.tostring(world, encoding='unicode'))
        launch = (ROOT/'launch/camera_lab.launch.py').read_text()
        ast.parse(launch)
        self.assertIn('sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo', launch)


if __name__ == '__main__':
    unittest.main()
