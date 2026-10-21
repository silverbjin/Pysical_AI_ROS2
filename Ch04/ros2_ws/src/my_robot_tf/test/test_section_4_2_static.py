"""4.2절 소스 정적 계약 검사. ROS/Gazebo가 필요하지 않다."""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestStaticTfContract(unittest.TestCase):
    def test_launch_has_two_static_publishers(self):
        source = (ROOT / "launch/multi_static_tf.launch.py").read_text()
        ast.parse(source)
        self.assertEqual(source.count('executable="static_transform_publisher"'), 2)
        self.assertIn('"--child-frame-id", "lidar_sensor_link"', source)
        self.assertIn('"--frame-id", "world", "--child-frame-id", "base_link"', source)

    def test_same_sensor_id_in_python_and_rviz(self):
        broadcaster = (ROOT / "my_robot_tf/static_tf_broadcaster.py").read_text()
        config = (ROOT / "rviz/multi_static_tf.rviz").read_text()
        self.assertIn("'lidar_sensor_link'", broadcaster)
        self.assertIn("lidar_sensor_link:", config)
        self.assertNotRegex(config, r"(?m)^\s*lidar:")


if __name__ == "__main__":
    unittest.main()
