"""Run: python -m unittest discover -s Ch06/tests -p 'test_section_6_1.py'"""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "1_simple_ik_concept.py"
spec = importlib.util.spec_from_file_location("ik_simple", SOURCE)
ik = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ik)


class IKNumericalTests(unittest.TestCase):
    def test_fk_jacobian_matches_finite_difference(self):
        theta = np.array([0.4, -0.7])
        numerical = np.column_stack([
            (ik.forward_kinematics(*(theta + 1e-6 * np.eye(2)[i]))
             - ik.forward_kinematics(*(theta - 1e-6 * np.eye(2)[i])))
            / 2e-6 for i in range(2)
        ])
        np.testing.assert_allclose(ik.compute_jacobian(*theta), numerical, atol=1e-8)

    def test_reachable_target_fk_error(self):
        solution = ik.inverse_kinematics_numerical(0.7, 0.0)
        self.assertIsNotNone(solution)
        self.assertLess(np.linalg.norm(ik.forward_kinematics(*solution) -
                                       np.array([0.7, 0.0])), 0.001)

    def test_workspace_rejects_outside_target(self):
        self.assertIsNone(ik.inverse_kinematics_numerical(1.2, 0.0))

    def test_nonconvergence_not_reported_as_success(self):
        self.assertIsNone(ik.inverse_kinematics_numerical(
            0.7, 0.0, max_iter=1
        ))

    def test_nonfinite_target_rejected(self):
        with self.assertRaises(ValueError):
            ik.inverse_kinematics_numerical(float("nan"), 0.0)


if __name__ == "__main__":
    unittest.main()
