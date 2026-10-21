"""4.7절 위치 제어 범위와 브리지 정적 테스트."""

import ast
import math
import unittest
from pathlib import Path

from my_robot_tf.joint_command_math import target_position

ROOT = Path(__file__).resolve().parents[1]


class TestJointControlContract(unittest.TestCase):
    def test_target_within_joint_limits(self):
        self.assertAlmostEqual(target_position("joint1", True), 0.785)
        self.assertAlmostEqual(target_position("joint2", False, 10), -1.57)

    def test_invalid_amplitude_and_name(self):
        for name, amplitude in [("wrong", 0.1), ("joint1", math.nan),
                                ("joint1", -0.1)]:
            with self.assertRaises(ValueError):
                target_position(name, True, amplitude)

    def test_bridge_and_client_topic_match(self):
        launch = (ROOT / "launch/joint_control_ch04.launch.py").read_text()
        client = (ROOT / "my_robot_tf/joint_position_cli.py").read_text()
        ast.parse(launch)
        ast.parse(client)
        self.assertIn('"/model/my_robot/joint1/cmd_pos"', launch)
        self.assertIn('"@std_msgs/msg/Float64]gz.msgs.Double"', launch)
        self.assertIn('("/model/my_robot/joint1/cmd_pos", "/joint1/cmd_pos")', launch)
        self.assertIn('f"/{joint_name}/cmd_pos"', client)


if __name__ == "__main__":
    unittest.main()
