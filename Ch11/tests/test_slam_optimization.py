"""11.6 time-aligned IMU gating and gravity-aligned 3D projection contracts."""
import importlib
import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
import yaml

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class AttitudeHistoryTests(unittest.TestCase):
    def setUp(self):
        try:
            self.core = importlib.import_module('my_quadruped_bot.sensors.attitude_history')
        except ModuleNotFoundError:
            self.fail('Missing time-aligned IMU history')
        self.h = self.core.AttitudeHistory(max_delta=0.03)

    def test_no_imu_or_stale_imu_never_assumes_horizontal(self):
        self.assertIsNone(self.h.nearest(1_000_000_000))
        self.h.add(1_000_000_000, (0, 0, 0, 1))
        self.assertIsNone(self.h.nearest(1_100_000_000))

    def test_nearest_stamp_wins_over_latest_received(self):
        q = (0, math.sin(.1), 0, math.cos(.1))
        self.h.add(1_000_000_000, q)
        self.h.add(1_020_000_000, (0, 0, 0, 1))
        self.assertEqual(self.h.nearest(1_001_000_000), q)

    def test_missing_or_invalid_orientation_blocks_nearest_sample(self):
        self.h.add(1_000_000_000, (0, 0, 0, 1))
        self.h.add(1_010_000_000, (0, 0, 0, 1), available=False)
        self.assertIsNone(self.h.nearest(1_010_000_000))
        self.h.add(1_020_000_000, (0, math.nan, 0, 1))
        self.assertIsNone(self.h.nearest(1_020_000_000))

    def test_time_reset_clears_old_orientation(self):
        self.h.add(10_000_000_000, (0, 0, 0, 1))
        self.h.add(1_000_000_000, (0, 0, 0, 1))
        self.assertIsNone(self.h.nearest(10_000_000_000))

    def test_quaternion_composition_accounts_for_mounting_rotation(self):
        q = (0, math.sin(.1), 0, math.cos(.1))
        inverse = (0, -math.sin(.1), 0, math.cos(.1))
        actual = self.core.multiply(q, inverse)
        for a, b in zip(actual, (0, 0, 0, 1)):
            self.assertAlmostEqual(a, b)

    def test_bad_history_parameters(self):
        for kwargs in ({'max_delta': -1}, {'max_delta': math.nan}, {'capacity': 0}):
            with self.assertRaises(ValueError):
                self.core.AttitudeHistory(**kwargs)


class ProjectionFrameTests(unittest.TestCase):
    def setUp(self):
        try:
            self.core = importlib.import_module('my_quadruped_bot.sensors.projection_frame')
        except ModuleNotFoundError:
            self.fail('Missing gravity-aligned projection frame')

    def test_preserves_xy_and_yaw_removes_tilt_and_uses_explicit_ground(self):
        roll, pitch, yaw = .2, -.3, .7
        c, s = math.cos, math.sin
        q = (s(roll/2)*c(pitch/2)*c(yaw/2)-c(roll/2)*s(pitch/2)*s(yaw/2),
             c(roll/2)*s(pitch/2)*c(yaw/2)+s(roll/2)*c(pitch/2)*s(yaw/2),
             c(roll/2)*c(pitch/2)*s(yaw/2)-s(roll/2)*s(pitch/2)*c(yaw/2),
             c(roll/2)*c(pitch/2)*c(yaw/2)+s(roll/2)*s(pitch/2)*s(yaw/2))
        pos, rotation = self.core.level_pose((1, 2, .4), q, ground_height=.1)
        self.assertEqual(pos, (1, 2, .1))
        self.assertEqual(rotation[:2], (0, 0))
        self.assertAlmostEqual(rotation[2], math.sin(yaw/2))

    def test_invalid_pose_rejected(self):
        for pos, q in (((math.inf,0,0), (0,0,0,1)), ((0,0,0),(0,0,0,0))):
            with self.assertRaises(ValueError):
                self.core.level_pose(pos, q)


class OptimizationAssetsTests(unittest.TestCase):
    def test_profiles_have_real_parameter_names_and_same_output(self):
        for profile, dim in (('balanced', 1.0), ('wide_search', 2.0)):
            p = PKG / f'config/mapper_params_{profile}.yaml'
            self.assertTrue(p.exists(), 'Missing tuning profile')
            d = yaml.safe_load(p.read_text())['slam_toolbox']['ros__parameters']
            self.assertEqual(d['correlation_search_space_dimension'], dim)
            self.assertGreaterEqual(d['minimum_travel_distance'], .3)
            self.assertGreaterEqual(d['transform_timeout'], .5)
            self.assertEqual(d['scan_topic'], '/scan_stabilized')
            self.assertNotIn('correlation_search_space', d)

    def test_projection_uses_distinct_level_frame_and_known_height_band(self):
        path = PKG / 'config/pointcloud_projection.yaml'
        self.assertTrue(path.exists(), 'Missing projection config')
        d = yaml.safe_load(path.read_text())['pointcloud_projection']['ros__parameters']
        self.assertEqual(d['target_frame'], 'scan_ground')
        self.assertEqual((d['min_height'], d['max_height']), (.3, 1.5))
        p = yaml.safe_load((PKG/'config/mapper_params_projection.yaml').read_text())['slam_toolbox']['ros__parameters']
        self.assertEqual((p['base_frame'],p['scan_topic']), ('scan_ground','/scan/projected'))

    def test_optional_3d_sensor_and_bridge(self):
        text = (PKG/'urdf/common/gazebo_control.xacro').read_text()
        self.assertIn('$(arg lidar_3d)', text)
        self.assertIn('<vertical>', text)
        path = PKG/'config/ros_gz_cloud_bridge.yaml'
        self.assertTrue(path.exists())
        d = yaml.safe_load(path.read_text())[0]
        self.assertEqual(d['ros_type_name'], 'sensor_msgs/msg/PointCloud2')
        self.assertEqual(d['gz_topic_name'], '/model/my_quadruped/scan/points')
        deps = {e.text for e in ET.parse(PKG/'package.xml').findall('exec_depend')}
        self.assertIn('pointcloud_to_laserscan', deps)

    def test_new_launches_and_executables_are_installable(self):
        for name in ('slam_optimized.launch.py', 'slam_3d.launch.py'):
            self.assertTrue((PKG/'launch'/name).exists(), name)
        setup = (PKG/'setup.py').read_text()
        for name in ('scan_stabilizer =', 'projection_frame ='):
            self.assertIn(name, setup)


if __name__ == '__main__':
    unittest.main()
