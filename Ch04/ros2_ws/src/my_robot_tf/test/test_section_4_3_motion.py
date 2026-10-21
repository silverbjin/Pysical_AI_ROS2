"""4.3절 원운동 수학·시간 계약 테스트 (ROS 의존성 없음)."""

import ast
import math
import unittest
from pathlib import Path

from my_robot_tf.trajectory_math import circle_pose, yaw_quaternion


class TestCircularMotion(unittest.TestCase):
    def test_quarter_turn(self):
        x, y, yaw = circle_pose(2.0, math.pi / 2)
        self.assertAlmostEqual(x, 0.0, places=8)
        self.assertAlmostEqual(y, 2.0, places=8)
        self.assertAlmostEqual(yaw, math.pi, places=8)

    def test_radius_invariant(self):
        for angle in (0, 0.2, 1.0, 4.0, 7.0):
            x, y, _ = circle_pose(2.0, angle)
            self.assertAlmostEqual(math.hypot(x, y), 2.0, places=8)

    def test_quaternion_normalized(self):
        for angle in (0.0, math.pi, 2 * math.pi):
            q = yaw_quaternion(angle)
            self.assertAlmostEqual(sum(v * v for v in q), 1.0, places=8)

    def test_invalid_radius(self):
        with self.assertRaises(ValueError):
            circle_pose(-1.0, 0.0)

    def test_dynamic_broadcaster_uses_elapsed_time(self):
        source = (Path(__file__).resolve().parents[1]
                  / "my_robot_tf/dynamic_tf_broadcaster.py").read_text()
        ast.parse(source)
        self.assertIn("self.angular_speed * dt", source)
        self.assertIn("now_ns < self.last_time_ns", source)
        self.assertIn("now.to_msg()", source)


if __name__ == "__main__":
    unittest.main()
