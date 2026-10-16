"""Regression checks for real sensor-based figure generation."""
import importlib
import importlib.util
import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

import yaml

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class ImuFigureTests(unittest.TestCase):
    def setUp(self):
        name = 'my_quadruped_bot.imu_visualization_math'
        self.assertIsNotNone(importlib.util.find_spec(name), 'Missing IMU pose conversion')
        self.convert = importlib.import_module(name).pose_components

    def test_places_imu_axes_at_observed_body_position(self):
        position, q = self.convert((0, 0, 0, 1), (1.0, 2.0, 0.3))
        self.assertEqual(position, (1.0, 2.0, 0.3))
        self.assertEqual(q, (0.0, 0.0, 0.0, 1.0))

    def test_preserves_90_degree_imu_rotation_without_double_rotation(self):
        q = (0.0, math.sqrt(0.5), 0.0, math.sqrt(0.5))
        _, actual = self.convert(q, (0, 0, 0.3))
        self.assertAlmostEqual(actual[1], math.sqrt(0.5))
        self.assertAlmostEqual(actual[3], math.sqrt(0.5))

    def test_rejects_invalid_or_unavailable_orientation(self):
        for q in ((0, 0, 0, 0), (math.nan, 0, 0, 1), (0, 0, 0, 10)):
            with self.assertRaises(ValueError):
                self.convert(q, (0, 0, 0))
        with self.assertRaises(ValueError):
            self.convert((0, 0, 0, 1), (0, 0, 0), orientation_available=False)

    def test_rejects_nonfinite_origin(self):
        with self.assertRaises(ValueError):
            self.convert((0, 0, 0, 1), (0, math.inf, 0))


class FigureAssetsTests(unittest.TestCase):
    def test_rviz_uses_real_scan_and_pose_axes(self):
        p = PKG / 'rviz/figure_11_2.rviz'
        self.assertTrue(p.exists(), 'Missing figure RViz configuration')
        config = yaml.safe_load(p.read_text())['Visualization Manager']
        self.assertEqual(config['Global Options']['Fixed Frame'], 'odom')
        displays = config['Displays']
        scan = next(d for d in displays if d['Class'] == 'rviz_default_plugins/LaserScan')
        self.assertEqual(scan['Topic']['Value'], '/scan')
        self.assertEqual(scan['Color'], '230; 25; 25')
        self.assertEqual(scan['Topic']['Reliability Policy'], 'Best Effort')
        pose = next(d for d in displays if d['Class'] == 'rviz_default_plugins/Pose')
        self.assertEqual(pose['Topic']['Value'], '/figure_11_2/imu_pose')
        self.assertEqual(pose['Shape'], 'Axes')

    def test_world_has_rendered_collidable_scan_targets(self):
        p = PKG / 'worlds/sensor_figure_world.sdf'
        self.assertTrue(p.exists(), 'Missing sensor target world')
        root = ET.parse(p).getroot()
        models = root.findall('.//world/model')
        targets = [m for m in models if m.attrib['name'] != 'ground_plane']
        self.assertGreaterEqual(len(targets), 4)
        for m in targets:
            self.assertIsNotNone(m.find('.//collision'))
            self.assertIsNotNone(m.find('.//visual'))
        sensors = root.find(".//plugin[@name='gz::sim::systems::Sensors']")
        self.assertIsNotNone(sensors)
        self.assertEqual(sensors.findtext('render_engine'), 'ogre2')


if __name__ == '__main__':
    unittest.main()
