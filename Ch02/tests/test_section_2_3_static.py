import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def parse(rel):
    path = ROOT / rel
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path)), source

class Section23(unittest.TestCase):
    def test_pose_log_is_throttled_without_throttling_subscription(self):
        tree, src = parse("ros2_ws/src/my_robot_system/my_robot_system/turtle_pose_subscriber.py")
        self.assertIn("time.monotonic()", src)
        self.assertIn("self._log_period = 0.5", src)
        self.assertIn("self.create_subscription(", src)
        self.assertIn("'/turtle1/pose'", src)
        self.assertNotIn("self.subscription \n", src)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=="TurtlePoseSubscriber")
        cb = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name=="listener_callback")
        self.assertTrue(any(isinstance(n,ast.If) for n in ast.walk(cb)))
if __name__ == "__main__": unittest.main()
