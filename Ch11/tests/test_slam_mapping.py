"""11.5: time-aligned tilt rejection and mapping integration contracts."""
import importlib
import importlib.util
import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
import yaml

CHAPTER = Path(__file__).resolve().parents[1]
PKG = CHAPTER / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class ScanGateTests(unittest.TestCase):
    def setUp(self):
        try:
            self.core = importlib.import_module('my_quadruped_bot.sensors.scan_gate')
        except ModuleNotFoundError:
            self.fail('Missing timestamp/tilt scan gate')
        self.gate = self.core.ScanGate(max_tilt_degrees=5.0, min_interval=0.15)

    def test_horizontal_and_yaw_rotated_scan_are_accepted(self):
        for q in ((0, 0, 0, 1), (0, 0, math.sqrt(.5), math.sqrt(.5))):
            gate = self.core.ScanGate()
            self.assertEqual(gate.check(1_000_000_000, 1_050_000_000, q), 'accepted')

    def test_pitch_or_roll_above_threshold_rejected(self):
        a = math.radians(6)/2
        for q in ((math.sin(a), 0, 0, math.cos(a)),
                  (0, math.sin(a), 0, math.cos(a)), (1, 0, 0, 0)):
            self.assertEqual(self.gate.check(1_000_000_000, 1_000_000_000, q), 'tilt')

    def test_invalid_quaternion_does_not_pass(self):
        for q in ((0, 0, 0, 0), (math.nan, 0, 0, 1), (0, 0, 0, 2)):
            self.assertEqual(self.gate.check(1_000_000_000, 1_000_000_000, q), 'orientation')

    def test_stale_future_zero_and_duplicate_scan_rejected(self):
        q = (0, 0, 0, 1)
        self.assertEqual(self.gate.check(0, 1_000_000_000, q), 'stamp')
        self.assertEqual(self.gate.check(1_000_000_000, 2_000_000_000, q), 'stale')
        self.assertEqual(self.gate.check(3_000_000_000, 2_000_000_000, q), 'future')
        self.assertEqual(self.gate.check(2_000_000_000, 2_000_000_000, q), 'accepted')
        self.assertEqual(self.gate.check(2_000_000_000, 2_010_000_000, q), 'interval')

    def test_dropped_tilt_scan_does_not_consume_interval(self):
        q = (0, 0, 0, 1)
        self.gate.check(1_000_000_000, 1_000_000_000, q)
        self.assertEqual(self.gate.check(1_150_000_000, 1_150_000_000, (1, 0, 0, 0)), 'tilt')
        self.assertEqual(self.gate.check(1_160_000_000, 1_160_000_000, q), 'accepted')

    def test_clock_rewind_resets_throttle(self):
        q = (0, 0, 0, 1)
        self.gate.check(10_000_000_000, 10_000_000_000, q)
        self.assertEqual(self.gate.check(1_000_000_000, 1_000_000_000, q), 'accepted')

    def test_bad_parameters_rejected(self):
        for kwargs in ({'max_tilt_degrees': -1}, {'max_tilt_degrees': 181},
                       {'min_interval': -1}, {'max_age': 0}, {'max_age': math.nan}):
            with self.assertRaises(ValueError):
                self.core.ScanGate(**kwargs)


class MappingIntegrationTests(unittest.TestCase):
    def test_real_jazzy_parameters_and_existing_frames(self):
        path = PKG / 'config/mapper_params_online_async.yaml'
        self.assertTrue(path.exists(), 'Missing executable mapping config')
        p = yaml.safe_load(path.read_text())['slam_toolbox']['ros__parameters']
        self.assertEqual((p['mode'], p['base_frame'], p['scan_topic']),
                         ('mapping', 'base_footprint', '/scan/slam'))
        self.assertGreater(p['transform_publish_period'], 0)
        self.assertEqual(p['ceres_linear_solver'], 'SPARSE_NORMAL_CHOLESKY')
        self.assertIn('loop_search_maximum_distance', p)
        for key in ('solver_type', 'loop_search_space', 'unknown_space_filled', 'map_start_x', 'map_start_y'):
            self.assertNotIn(key, p)

    def test_official_launch_handles_lifecycle_without_second_ekf(self):
        path = PKG / 'launch/slam.launch.py'
        self.assertTrue(path.exists(), 'Missing SLAM launch')
        text = path.read_text()
        self.assertIn('online_async_launch.py', text)
        self.assertIn("'autostart': 'true'", text)
        self.assertNotIn("'localization.launch.py'", text)
        self.assertNotIn("executable='ekf_node'", text)

    def test_simulation_launch_is_renamed_and_still_localizes_once(self):
        path = PKG / 'launch/SLAM_simulation.launch.py'
        self.assertTrue(path.exists(), 'Requested launch name absent')
        self.assertFalse((PKG / 'launch/figure_11_2.launch.py').exists())
        self.assertEqual(path.read_text().count("'localization.launch.py'"), 1)
        script = (CHAPTER / 'scripts/run_figure_11_2.sh').read_text()
        self.assertIn('SLAM_simulation.launch.py', script)

    def test_rviz_map_qos_and_dependencies(self):
        path = PKG / 'rviz/slam.rviz'
        self.assertTrue(path.exists(), 'Missing mapping RViz config')
        p = yaml.safe_load(path.read_text())['Visualization Manager']
        self.assertEqual(p['Global Options']['Fixed Frame'], 'map')
        m = next(x for x in p['Displays'] if x['Class'] == 'rviz_default_plugins/Map')
        self.assertEqual(m['Topic']['Value'], '/map')
        self.assertEqual(m['Topic']['Durability Policy'], 'Transient Local')
        deps = {x.text for x in ET.parse(PKG / 'package.xml').findall('exec_depend')}
        self.assertTrue({'slam_toolbox', 'nav2_map_server', 'teleop_twist_keyboard'} <= deps)


class MapProbeTests(unittest.TestCase):
    def test_map_cell_statistics_and_shape_validation(self):
        path = CHAPTER / 'scripts/check_slam_mapping.py'
        self.assertTrue(path.exists(), 'Missing runtime probe')
        spec = importlib.util.spec_from_file_location('check_slam_mapping', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        good = module.map_summary(2, 2, 0.05, 'map', [-1, 0, 100, 50])
        self.assertTrue(good['valid'])
        self.assertEqual((good['known_cells'], good['free_cells'], good['occupied_cells']), (3, 1, 1))
        self.assertFalse(module.map_summary(2, 2, 0.05, 'map', [0])['valid'])
        self.assertFalse(module.map_summary(1, 1, 0.05, 'odom', [0])['valid'])


if __name__ == '__main__':
    unittest.main()
