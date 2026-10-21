"""Exercise the real IMU callback frame guard without requiring ROS imports."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

SOURCE = Path(__file__).resolve().parents[1] / (
    'ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/imu_processor.py')


class ImuFrameRegression(unittest.TestCase):
    def test_wrong_mount_frame_is_rejected_before_filter(self):
        tree = ast.parse(SOURCE.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and
                   n.name == 'ImuProcessor')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and
                      n.name == 'imu_callback')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), 'exec'), ns)
        warnings = []
        node = NS(get_logger=lambda: NS(warning=lambda *a, **k: warnings.append(a)),
                  filter=NS(update=lambda *a, **k: self.fail('Filter received wrong frame')))
        ns['imu_callback'](node, NS(header=NS(frame_id='tilted_sensor')))
        self.assertEqual(len(warnings), 1)


if __name__ == '__main__':
    unittest.main()
