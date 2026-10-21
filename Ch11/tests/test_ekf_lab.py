"""Regression contracts for the isolated 11.4 EKF exercise."""
import importlib
import math
from pathlib import Path
import sys
import unittest
import yaml

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class CommandOdometryTests(unittest.TestCase):
    def setUp(self):
        try:
            self.core = importlib.import_module('my_quadruped_bot.localization.lab_math')
        except ModuleNotFoundError:
            self.fail('Missing isolated EKF exercise core')

    def test_scale_integrates_command_not_observed_motion(self):
        f = self.core.CommandOdometry(scale=0.9, noise_stddev=0.0, angular_noise_stddev=0.0)
        f.step(0)
        for i in range(10):
            f.set_command(1.0, 0, 0, i*100_000_000)
            s = f.step((i+1)*100_000_000)
        self.assertAlmostEqual(s.x, 0.9)

    def test_timeout_stops_phantom_motion(self):
        f = self.core.CommandOdometry(noise_stddev=0.0, timeout=0.2)
        f.step(0)
        f.set_command(1, 0, 0, 0)
        f.step(100_000_000)
        s = f.step(200_000_000)
        before = s.x
        for i in range(3, 10):
            s = f.step(i*100_000_000)
        self.assertAlmostEqual(s.x, before)
        self.assertEqual(s.vx, 0.0)

    def test_clock_reset_clears_command_and_pose(self):
        f = self.core.CommandOdometry(noise_stddev=0)
        f.step(1_000_000_000)
        f.set_command(1, 0, 0, 1_000_000_000)
        f.step(1_100_000_000)
        s = f.step(0)
        self.assertEqual((s.x, s.y, s.yaw, s.vx), (0, 0, 0, 0))

    def test_long_clock_gap_is_not_integrated(self):
        f = self.core.CommandOdometry(noise_stddev=0)
        f.step(0)
        f.set_command(1, 0, 0, 0)
        self.assertEqual(f.step(10_000_000_000).x, 0)

    def test_noise_seed_is_reproducible(self):
        a = self.core.CommandOdometry(seed=7)
        b = self.core.CommandOdometry(seed=7)
        for f in (a, b):
            f.step(0)
            f.set_command(0.1, 0, 0, 0)
        self.assertEqual(a.step(10_000_000), b.step(10_000_000))

    def test_nonfinite_command_rejected(self):
        f = self.core.CommandOdometry()
        with self.assertRaises(ValueError):
            f.set_command(math.nan, 0, 0, 0)

    def test_unknown_covariance_replaced_without_changing_known_covariance(self):
        cov = self.core.covariance3([0.0]*9, 0.04)
        self.assertEqual([cov[i] for i in (0, 4, 8)], [0.04]*3)
        self.assertEqual(self.core.covariance3(cov, 0.01), cov)
        missing = [-1.0]+[0.0]*8
        self.assertEqual(self.core.covariance3(missing, 0.01), missing)

    def test_invalid_parameters_rejected(self):
        for kw in ({'scale': -1}, {'noise_stddev': -0.1}, {'timeout': 0}):
            with self.assertRaises(ValueError):
                self.core.CommandOdometry(**kw)


class EkfWiringTests(unittest.TestCase):
    def load_profile(self, name):
        p = PKG/'config'/name
        self.assertTrue(p.exists(), 'Missing runnable EKF lab profile')
        return yaml.safe_load(p.read_text())['ekf_lab_filter']['ros__parameters']

    def test_default_lab_isolated_and_velocity_only(self):
        p = self.load_profile('ekf_command_lab.yaml')
        self.assertFalse(p['publish_tf'])
        self.assertEqual(p['odom0'], '/ekf_lab/raw')
        self.assertEqual(p['imu0'], '/ekf_lab/imu')
        self.assertEqual(p['base_link_frame'], 'base_footprint')
        self.assertEqual(len(p['odom0_config']), 15)
        self.assertFalse(any(p['odom0_config'][:6]))
        self.assertTrue(p['odom0_config'][6])
        self.assertTrue(p['use_sim_time'])
        self.assertFalse(any(p['imu0_config'][12:]))
        self.assertNotIn('process_noise_covariance', p)

    def test_acceleration_profile_explicitly_removes_gravity(self):
        p = self.load_profile('ekf_command_lab_accel.yaml')
        self.assertTrue(p['imu0_remove_gravitational_acceleration'])
        self.assertTrue(all(p['imu0_config'][12:]))
        self.assertFalse(p['imu0_relative'])
        self.assertFalse(p['publish_tf'])

    def test_existing_observed_localization_remains_default(self):
        p = yaml.safe_load((PKG/'config/ekf.yaml').read_text())['ekf_filter_node']['ros__parameters']
        self.assertTrue(p['publish_tf'])
        self.assertEqual(p['odom0'], '/odom/raw')


if __name__ == '__main__':
    unittest.main()
