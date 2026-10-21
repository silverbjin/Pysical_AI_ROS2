"""4.4절 프레임·파라미터 정적 검사 (ROS 실행 불필요)."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestTrackingContract(unittest.TestCase):
    def test_listener_parameters_and_lookup(self):
        code = (ROOT / "my_robot_tf/tf_listener.py").read_text()
        ast.parse(code)
        self.assertIn('self.declare_parameter("target_frame", "world")', code)
        self.assertIn('self.declare_parameter("source_frame", "turtle_frame")', code)
        self.assertIn("self.target_frame, self.source_frame, rclpy.time.Time()", code)
        self.assertIn("except TransformException", code)
        self.assertIn("math.hypot(x, y)", code)

    def test_demo_connected_frames(self):
        launch = (ROOT / "launch/tracking_demo.launch.py").read_text()
        ast.parse(launch)
        self.assertIn('"--child-frame-id", "police_bot"', launch)
        self.assertIn('"target_frame": "police_bot"', launch)
        self.assertIn('"source_frame": "turtle_frame"', launch)


if __name__ == "__main__":
    unittest.main()
