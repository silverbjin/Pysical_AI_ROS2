import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def read_and_parse(path):
    source = (ROOT / path).read_text(encoding="utf-8")
    return ast.parse(source), source

class Section28(unittest.TestCase):
    def test_explicit_qos_and_no_frames_diagnostics(self):
        tree, src = read_and_parse("ros2_ws/src/my_robot_system/my_robot_system/qos_compare_subscriber.py")
        for text in ("ReliabilityPolicy.RELIABLE","ReliabilityPolicy.BEST_EFFORT",
                     "self.create_subscription(", "received_count = 0",
                     "self.create_timer(3.0, self.warn_if_no_frames)", "if self.received_count == 0:"):
            self.assertIn(text, src)
        _, src_pub = read_and_parse("ros2_ws/src/my_robot_system/my_robot_system/qos_test_node.py")
        self.assertIn("ReliabilityPolicy.BEST_EFFORT", src_pub)
        self.assertIn("DurabilityPolicy.VOLATILE", src_pub)
        self.assertIn("depth=1", src_pub)
if __name__ == "__main__": unittest.main()
