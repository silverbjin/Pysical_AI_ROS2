"""Launch file AST contract tests; no ROS imports required."""
import ast
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_moveit_config/launch/Gazebo_moveit.launch.py"
text = p.read_text(encoding="utf-8")


class GazeboLaunchTests(unittest.TestCase):
    def test_parseable_ast(self):
        self.assertIsInstance(ast.parse(text), ast.Module)

    def test_spawn_precedes_controller_handlers(self):
        self.assertIn("OnProcessExit(", text)
        self.assertIn("target_action=spawn_entity", text)
        self.assertIn("on_exit=[joint_state_broadcaster_spawner, arm_controller_spawner]", text)

    def test_manager_timeout(self):
        self.assertEqual(text.count('"--controller-manager-timeout"'), 2)

    def test_clock_bridge_present(self):
        self.assertIn("/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock", text)

    def test_one_ros2_control_owner(self):
        self.assertNotIn('executable="ros2_control_node"', text)
        self.assertIn("my_robot.ros2_control_gazebo.urdf.xacro", text)


if __name__ == "__main__":
    unittest.main()
