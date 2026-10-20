import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def parse(rel):
    path = ROOT / rel
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path)), source

class Section21(unittest.TestCase):
    def test_python_syntax_and_pure_sensor_step(self):
        tree, src = parse("ros2_ws/src/my_robot_system/my_robot_system/joint_sensor_node.py")
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "advance_sensor_state")
        namespace = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "<step>", "exec"), namespace)
        advance = namespace["advance_sensor_state"]
        self.assertEqual(advance(0.0, 100.0, 0.1), (0.1, 99.9))
        self.assertEqual(advance(1.56, 0.05, 0.2), (1.57, 0.0))
        self.assertEqual(advance(-1.56, -10.0, -0.2), (-1.57, 0.0))
        self.assertIn("self.joint_angle, self.battery_level = advance_sensor_state(", src)
    def test_timer_and_entrypoint(self):
        _, src = parse("ros2_ws/src/my_robot_system/my_robot_system/joint_sensor_node.py")
        self.assertIn("self.create_timer(self.timer_period, self.timer_callback)", src)
        self.assertIn("rclpy.spin(node)", src)

if __name__ == "__main__": unittest.main()
