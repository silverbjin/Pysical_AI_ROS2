import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def read_and_parse(path):
    source = (ROOT / path).read_text(encoding="utf-8")
    return ast.parse(source), source

class Section27(unittest.TestCase):
    def test_patrol_has_bounded_server_wait_angle_wrap_and_result_guard(self):
        tree, src = read_and_parse("ros2_ws/src/my_robot_system/my_robot_system/turtle_patrol.py")
        self.assertIn("raise TimeoutError('SetPen service", src)
        self.assertIn("wait_for_server(timeout_sec=5.0)", src)
        self.assertIn("math.atan2(math.sin(target_theta), math.cos(target_theta))", src)
        self.assertIn("wrapped.status != GoalStatus.STATUS_SUCCEEDED", src)
        self.assertIn("self.pose_initialized = True", src)
        self.assertIn("self.state = 'IDLE'", src)
    def test_launch_remaps_both_endpoints(self):
        _, src = read_and_parse("ros2_ws/src/my_robot_system/launch/remap_fixed.launch.py")
        self.assertEqual(src.count("('/turtle1/cmd_vel', '/cmd_vel_custom')"), 2)
if __name__ == "__main__": unittest.main()
