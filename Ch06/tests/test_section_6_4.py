"""Static API and safety contract tests without ROS dependencies."""
import ast
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_control/my_robot_control/hello_moveit.py"
source = p.read_text(encoding="utf-8")
tree = ast.parse(source)


class MoveItCommandTests(unittest.TestCase):
    def test_valid_python_ast(self):
        self.assertIsInstance(tree, ast.Module)

    def test_no_forced_process_exit(self):
        self.assertNotIn("os._exit", source)

    def test_plan_only_default(self):
        self.assertIn('parser.add_argument("--execute", action="store_true"', source)

    def test_actual_tip_and_description_package(self):
        self.assertIn('pose_link="link_wrist"', source)
        self.assertIn('get_package_share_directory("my_robot_description")', source)

    def test_no_false_execution_success_claim(self):
        self.assertNotIn('print("Execution Success")', source)
        self.assertIn("EXECUTION RESULT", source)


if __name__ == "__main__":
    unittest.main()
