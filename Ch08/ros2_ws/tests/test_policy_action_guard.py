"""Pure Python static logic checks: no MuJoCo/ROS dependency."""
import unittest
from policy_action_guard import SimulationActionGuard, SafetyReject


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = SimulationActionGuard()
        self.kw = dict(now=10.0, sensor_time=9.9, command_time=9.9,
                       authority=True, estop=False)

    def test_safe_zero(self):
        self.assertEqual(self.guard.accept([0] * 6, **self.kw), (0,) * 6)

    def test_no_hardware(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0] * 6, simulation_only=False, **self.kw)

    def test_estop(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0] * 6, **{**self.kw, "estop": True})

    def test_no_authority(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0] * 6, **{**self.kw, "authority": False})

    def test_sensor_staleness(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0] * 6, **{**self.kw, "sensor_time": 9.0})

    def test_future_stamp(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0] * 6, **{**self.kw, "command_time": 11.0})

    def test_nonfinite(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([float("nan")] + [0] * 5, **self.kw)

    def test_joint_count(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0] * 3, **self.kw)

    def test_initial_limit(self):
        with self.assertRaises(SafetyReject):
            self.guard.accept([0.5] + [0] * 5, **self.kw)

    def test_slew_rate(self):
        self.guard.accept([0] * 6, **self.kw)
        with self.assertRaises(SafetyReject):
            self.guard.accept([0.5] + [0] * 5, **{**self.kw, "now": 10.01,
                                           "sensor_time": 10.01,
                                           "command_time": 10.01})

    def test_slew_accept(self):
        self.guard.accept([0] * 6, **self.kw)
        self.assertEqual(self.guard.accept([0.1] + [0] * 5,
                         **{**self.kw, "now": 10.1,
                            "sensor_time": 10.1,
                            "command_time": 10.1})[0], 0.1)


if __name__ == "__main__":
    unittest.main()
