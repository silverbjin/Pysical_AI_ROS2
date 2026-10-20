import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def read_and_parse(path):
    source = (ROOT / path).read_text(encoding="utf-8")
    return ast.parse(source), source

class Section26(unittest.TestCase):
    def test_action_client_reports_failure_with_nonzero_exit(self):
        tree, src = read_and_parse("ros2_ws/src/my_robot_system/my_robot_system/count_until_client.py")
        self.assertIn("return 0 if node.success else 1", src)
        self.assertIn("raise SystemExit(main())", src)
        self.assertIn("except Exception as exc:", src)
        self.assertIn("self.finished = True", src)
        self.assertIn("GoalStatus.STATUS_SUCCEEDED", src)
    def test_server_executor_is_reentrant_and_cancelable(self):
        tree, src = read_and_parse("ros2_ws/src/my_robot_system/my_robot_system/count_until_server.py")
        for token in ("ReentrantCallbackGroup()", "callback_group=self.callback_group", "MultiThreadedExecutor", "goal_handle.is_cancel_requested", "math.isfinite(period)"):
            self.assertIn(token, src)
if __name__ == "__main__": unittest.main()
