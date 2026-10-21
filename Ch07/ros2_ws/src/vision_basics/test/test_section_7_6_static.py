"""Section-specific ROS-free static regression tests (not simulator proof)."""
import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class TestSection76(unittest.TestCase):
    def test_gripper_and_controller_contract(self):
        src = (ROOT/'vision_basics/gripper_controller.py').read_text()
        ast.parse(src)
        self.assertIn("OPEN_M = 0.0", src)
        self.assertIn("self.send_position(self.CLOSE_M, 'CLOSING')", src)
        self.assertIn('response.result.error_code != 0', src)
        cfg = (ROOT.parent/'my_robot_moveit_config/config/ros2_controllers.yaml').read_text()
        self.assertIn('joint_trajectory_controller/JointTrajectoryController', cfg)
        self.assertIn('joints: [joint_finger1, joint_finger2]', cfg)


if __name__ == '__main__':
    unittest.main()
