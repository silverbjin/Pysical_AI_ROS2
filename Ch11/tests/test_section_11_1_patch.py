"""ROS-independent checks of the real demo callback extracted from source AST."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

SOURCE = Path(__file__).resolve().parents[1] / (
    'ros2_ws/src/my_quadruped_bot/my_quadruped_bot/command_odometry_demo.py')


def callback():
    tree = ast.parse(SOURCE.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and
               n.name == 'CommandOdometryDemo')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and
                  n.name == 'cmd_vel_callback')
    namespace = {'math': math}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['cmd_vel_callback']


class SafetyRegression(unittest.TestCase):
    def setUp(self):
        self.warnings = []
        self.node = NS(vx=1.0, vy=1.0, vth=1.0, last_cmd_time=None,
                       get_clock=lambda: NS(now=lambda: 'stamp'),
                       get_logger=lambda: NS(warning=self.warnings.append))
        self.run_callback = callback()

    def test_nonfinite_command_is_not_integrated(self):
        self.run_callback(self.node, NS(linear=NS(x=math.nan, y=0), angular=NS(z=0)))
        self.assertEqual((self.node.vx, self.node.vy, self.node.vth), (0, 0, 0))
        self.assertTrue(self.warnings)

    def test_finite_command_preserves_teaching_scale(self):
        self.run_callback(self.node, NS(linear=NS(x=1, y=0.2), angular=NS(z=-1)))
        self.assertAlmostEqual(self.node.vx, 0.9)
        self.assertAlmostEqual(self.node.vy, 0.18)
        self.assertAlmostEqual(self.node.vth, -0.9)

    def test_rewind_and_pause_guards_exist(self):
        cls = next(n for n in ast.parse(SOURCE.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'CommandOdometryDemo')
        update = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'update_odometry')
        self.assertTrue(any(isinstance(n, ast.Compare) and
                            isinstance(n.ops[0], ast.Lt) and isinstance(n.left, ast.Name)
                            and n.left.id == 'dt' for n in ast.walk(update)))
        self.assertTrue(any(isinstance(n, ast.Compare) and
                            isinstance(n.ops[0], ast.Gt) and isinstance(n.left, ast.Name)
                            and n.left.id == 'dt' for n in ast.walk(update)))


if __name__ == '__main__':
    unittest.main()
