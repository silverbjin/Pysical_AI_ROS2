import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def parse(rel):
    path = ROOT / rel
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path)), source

class Section24(unittest.TestCase):
    def test_client_has_bounded_service_wait_and_failure_exit(self):
        tree, src = parse("ros2_ws/src/my_robot_system/my_robot_system/turtle_spawn_client.py")
        self.assertIn("range(5)", src)
        self.assertIn("timeout_sec=5.0", src)
        self.assertIn("raise SystemExit(1)", src)
        self.assertIn("client_node.destroy_node()", src)
        self.assertIn("if rclpy.ok():", src)
        self.assertIn("self.future.exception()", src)
        self.assertIn("self.client.call_async(self.req)", src)
if __name__ == "__main__": unittest.main()
