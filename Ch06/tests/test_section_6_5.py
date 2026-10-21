"""Syntax and geometry contract checks without ROS dependencies."""
import ast
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_control/my_robot_control/cartesian_path.py"
source = p.read_text(encoding="utf-8")
tree = ast.parse(source)


class CartesianContractTests(unittest.TestCase):
    def test_parseable_python(self):
        self.assertIsInstance(tree, ast.Module)

    def test_plan_only_execution_guard(self):
        self.assertIn('parser.add_argument("--execute", action="store_true"', source)
        self.assertIn("offsets if args.execute else offsets[:1]", source)

    def test_has_pilz_lin_config(self):
        self.assertIn('"planner_id": "LIN"', source)
        self.assertIn('"pilz_industrial_motion_planner"', source)

    def test_offsets_form_closed_xz_square(self):
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "square_offsets")
        self.assertTrue(any(isinstance(n, ast.Return) for n in ast.walk(node)))
        self.assertIn("(-size, 0.0, 0.0)", source)

    def test_no_false_jump_threshold_or_exit(self):
        self.assertNotIn("jump_threshold=0.0", source)
        self.assertNotIn("os._exit", source)


if __name__ == "__main__":
    unittest.main()
