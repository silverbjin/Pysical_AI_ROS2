"""2-DOF safety diagnostic unit tests; no ROS packages required."""
import importlib.util
import math
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "5_ik_safety_diagnostics.py"
spec = importlib.util.spec_from_file_location("safe_diagnostic", p)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class DiagnosticTests(unittest.TestCase):
    def test_stretched_arm_is_singular(self):
        result = d.diagnose((0.0, 0.0), (0.7, 0.0))
        self.assertEqual(result["verdict"], "NEAR_SINGULAR")
        self.assertLess(result["min_singular_value"], 1e-5)

    def test_unreachable_target(self):
        self.assertEqual(d.diagnose((0.1, 0.1), (1.2, 0.0))["verdict"], "UNREACHABLE")

    def test_bounded_step(self):
        result = d.diagnose((0.2, -0.3), (0.1, 0.5), max_step=0.07)
        self.assertLessEqual(math.hypot(*result["step_rad"]), 0.0700000001)

    def test_joint_limit(self):
        result = d.diagnose((0.2, 0.2), (0.0, 0.8), limits=(-0.2, 0.2))
        self.assertTrue(all(-0.2 <= x <= 0.2 for x in result["next_joint_rad"]))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            d.diagnose((0.0, float("inf")), (0.1, 0.1))


if __name__ == "__main__":
    unittest.main()
