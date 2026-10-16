"""Exercise the textbook complementary filter without a ROS installation."""
import importlib
import math
from pathlib import Path
import sys
import unittest

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class ComplementaryFilterTests(unittest.TestCase):
    def setUp(self):
        try:
            module = importlib.import_module('my_quadruped_bot.sensors.complementary_filter')
        except ModuleNotFoundError:
            self.fail('Missing installable sensors complementary filter')
        self.Filter = module.ComplementaryFilter

    def test_stationary_level_has_zero_rpy(self):
        f = self.Filter()
        self.assertEqual(f.update(0, (0, 0, 9.81), (0, 0, 0)), (0, 0, 0))
        self.assertEqual(f.update(10_000_000, (0, 0, 9.81), (0, 0, 0)), (0, 0, 0))

    def test_initial_tilt_comes_from_acceleration_not_zero(self):
        roll = 0.3
        f = self.Filter()
        result = f.update(0, (0, 9.81*math.sin(roll), 9.81*math.cos(roll)), (0, 0, 0))
        self.assertAlmostEqual(result[0], roll)

    def test_pitch_sign(self):
        pitch = 0.2
        result = self.Filter().update(
            0, (-9.81*math.sin(pitch), 0, 9.81*math.cos(pitch)), (0, 0, 0))
        self.assertAlmostEqual(result[1], pitch)

    def test_matches_book_equation_for_small_angles(self):
        f = self.Filter(alpha=0.98)
        f.update(0, (0, 0, 9.81), (0, 0, 0))
        result = f.update(100_000_000, (0, 9.81*math.sin(0.2), 9.81*math.cos(0.2)), (1, 0, 0))
        self.assertAlmostEqual(result[0], 0.98*0.1+0.02*0.2)

    def test_yaw_integrates_using_sensor_time_and_has_drift(self):
        f = self.Filter()
        f.update(0, (0, 0, 9.81), (0, 0, 0.1))
        for i in range(1, 101):
            result = f.update(i*10_000_000, (0, 0, 9.81), (0, 0, 0.1))
        self.assertAlmostEqual(result[2], 0.1)

    def test_duplicate_stamp_does_not_integrate_twice(self):
        f = self.Filter()
        f.update(10, (0, 0, 9.81), (0, 0, 1))
        self.assertIsNone(f.update(10, (0, 0, 9.81), (0, 0, 1)))

    def test_clock_reversal_reinitializes_in_new_time_epoch(self):
        f = self.Filter()
        f.update(2_000_000_000, (0, 0, 9.81), (0, 0, 1))
        f.update(2_100_000_000, (0, 0, 9.81), (0, 0, 1))
        self.assertEqual(f.update(0, (0, 0, 9.81), (0, 0, 1)), (0, 0, 0))
        self.assertAlmostEqual(f.update(100_000_000, (0, 0, 9.81), (0, 0, 1))[2], 0.1)

    def test_long_gap_does_not_invent_rotation_for_missing_samples(self):
        f = self.Filter(max_dt=0.2)
        f.update(0, (0, 0, 9.81), (0, 0, 1))
        self.assertEqual(f.update(5_000_000_000, (0, 0, 9.81), (0, 0, 1)), (0, 0, 0))

    def test_nan_and_zero_acceleration_do_not_poison_state(self):
        f = self.Filter()
        f.update(0, (0, 0, 9.81), (0, 0, 0))
        for a, g in (((0, 0, 0), (0, 0, 0)), ((0, 0, 9.81), (math.nan, 0, 0))):
            with self.assertRaises(ValueError):
                f.update(50_000_000, a, g)
        self.assertAlmostEqual(f.update(100_000_000, (0, 0, 9.81), (0, 0, 1))[2], 0.1)

    def test_roll_wrap_uses_shortest_angle_correction(self):
        f = self.Filter(alpha=0.98)
        f.update(0, (0, math.sin(3.13), math.cos(3.13)), (0, 0, 0))
        result = f.update(10_000_000, (0, math.sin(-3.13), math.cos(-3.13)), (0, 0, 0))
        self.assertGreater(abs(result[0]), 3.12)

    def test_invalid_parameters_are_rejected(self):
        for kwargs in ({'alpha': -0.1}, {'alpha': 1.1}, {'alpha': math.nan}, {'max_dt': 0}):
            with self.assertRaises(ValueError):
                self.Filter(**kwargs)


if __name__ == '__main__':
    unittest.main()
