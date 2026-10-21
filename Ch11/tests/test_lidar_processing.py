"""Book section 11.3.4: scan geometry, invalid data and freshness."""
import importlib
import math
from pathlib import Path
import sys
import unittest

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class LidarProcessingTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module('my_quadruped_bot.sensors.lidar_processing')
        except ModuleNotFoundError:
            self.fail('Missing LiDAR processing core')
        self.analyze = self.module.analyze_front_sector

    def scan(self, ranges=None, **kwargs):
        return self.analyze([2.0]*361 if ranges is None else ranges,
                            -math.pi, math.pi/180, 0.1, 10.0, **kwargs)

    def test_forward_obstacle_and_rear_exclusion(self):
        ranges = [2.0]*361
        ranges[0] = 0.2
        self.assertEqual(self.scan(ranges).state, 'CLEAR')
        ranges[180] = 0.3
        result = self.scan(ranges)
        self.assertEqual(result.state, 'OBSTACLE')
        self.assertAlmostEqual(result.min_distance, 0.3)

    def test_clear_full_sector(self):
        result = self.scan()
        self.assertEqual(result.state, 'CLEAR')
        self.assertTrue(result.coverage_complete)
        self.assertGreater(result.valid_count, 50)

    def test_angle_wrap_zero_to_360_degrees(self):
        ranges = [2.0]*361
        ranges[355] = 0.25
        result = self.analyze(ranges, 0.0, math.pi/180, 0.1, 10.0)
        self.assertEqual(result.state, 'OBSTACLE')

    def test_reverse_scan_direction(self):
        ranges = [2.0]*361
        ranges[180] = 0.2
        self.assertEqual(self.analyze(ranges, math.pi, -math.pi/180, 0.1, 10.0).state,
                         'OBSTACLE')

    def test_rejects_nan_inf_and_out_of_sensor_range(self):
        ranges = [2.0]*361
        for index, value in zip(range(176, 181), (math.nan, math.inf, -1.0, 0.05, 11.0)):
            ranges[index] = value
        result = self.scan(ranges)
        self.assertEqual(result.invalid_count, 5)
        self.assertEqual(result.state, 'UNKNOWN')
        self.assertEqual(result.min_distance, 2.0)

    def test_all_inf_and_empty_are_unknown_not_safe(self):
        for ranges in ([math.inf]*361, []):
            result = self.scan(ranges)
            self.assertEqual(result.state, 'UNKNOWN')
            self.assertIsNone(result.min_distance)

    def test_close_return_wins_even_if_other_samples_invalid(self):
        ranges = [math.nan]*361
        ranges[180] = 0.2
        self.assertEqual(self.scan(ranges).state, 'OBSTACLE')

    def test_partial_forward_fov_is_not_complete_clearance(self):
        result = self.analyze([2.0]*11, -math.radians(5), math.pi/180, 0.1, 10.0)
        self.assertEqual(result.state, 'UNKNOWN')
        self.assertFalse(result.coverage_complete)

    def test_threshold_is_inclusive_for_conservative_warning(self):
        # A return exactly at the safety boundary must not be declared CLEAR.
        self.assertEqual(self.scan([0.5]*361).state, 'OBSTACLE')
        self.assertEqual(self.scan([0.49]*361).state, 'OBSTACLE')
        self.assertEqual(self.scan([0.51]*361).state, 'CLEAR')

    def test_invalid_metadata_rejected(self):
        for inc, lo, hi in ((0, 0.1, 10), (math.nan, 0.1, 10), (0.01, 10, 1)):
            with self.assertRaises(ValueError):
                self.analyze([1.0]*361, -math.pi, inc, lo, hi)

    def test_invalid_parameters_rejected(self):
        for kwargs in ({'safe_distance': 0}, {'scope_deg': 0}, {'scope_deg': 181}):
            with self.assertRaises(ValueError):
                self.scan(**kwargs)

    def test_freshness_catches_delayed_and_paused_input(self):
        fresh = self.module.scan_is_fresh
        self.assertTrue(fresh(5.0, 5.1, 10.0, 10.1, 0.5))
        self.assertFalse(fresh(5.0, 6.0, 10.0, 10.1, 0.5))
        self.assertFalse(fresh(5.0, 5.0, 10.0, 11.0, 0.5))
        self.assertFalse(fresh(6.0, 5.0, 10.0, 10.1, 0.5))
        self.assertFalse(fresh(None, 5.0, None, 10.0, 0.5))


if __name__ == '__main__':
    unittest.main()
