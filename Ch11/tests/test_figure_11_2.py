"""Regression checks for real sensor-based figure generation."""
import importlib
import importlib.util
import math
import shutil
import subprocess
import tempfile
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
    @unittest.skipUnless(importlib.util.find_spec('rclpy'), 'Requires ROS Python')
    def test_standing_commands_reach_targets_in_actual_urdf(self):
        import numpy as np
        from my_quadruped_bot.trot_controllerFSM import TrotController

        urdf = subprocess.run(['xacro', str(PKG / 'urdf/robot.urdf.xacro')],
                              capture_output=True, text=True, check=True, timeout=30)
        joints = {j.get('name'): j for j in ET.fromstring(urdf.stdout).findall('joint')}
        controller = TrotController()
        for height in (controller.idle_height, controller.target_height):
            for leg, target in controller.get_nominal_foot_positions(height).items():
                angles = controller._solve_leg_ik(leg, target)
                transform = np.eye(4)
                for kind, angle in zip(('hip', 'thigh', 'calf', 'foot'), [*angles, 0]):
                    joint = joints[f'{leg.lower()}_{kind}_' + ('fixed' if kind == 'foot' else 'joint')]
                    origin = joint.find('origin')
                    xyz = [float(v) for v in origin.get('xyz').split()]
                    roll, pitch, yaw = [float(v) for v in origin.get('rpy').split()]
                    def rotation(axis, value):
                        c, s = math.cos(value), math.sin(value)
                        if axis == 'x':
                            return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
                        if axis == 'y':
                            return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
                        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
                    step = np.eye(4)
                    step[:3, 3] = xyz
                    step[:3, :3] = rotation('z', yaw) @ rotation('y', pitch) @ rotation('x', roll)
                    if kind != 'foot':
                        limit = joint.find('limit')
                        self.assertGreaterEqual(angle, float(limit.get('lower')))
                        self.assertLessEqual(angle, float(limit.get('upper')))
                        step[:3, :3] = step[:3, :3] @ rotation('x' if kind == 'hip' else 'y', angle)
                    transform = transform @ step
                np.testing.assert_allclose(transform[:3, 3], target, atol=1e-6,
                                           err_msg=f'{leg} at height {height}')

    @unittest.skipUnless(shutil.which('xacro') and shutil.which('gz'),
                         'Requires ROS xacro and Gazebo CLI')
    def test_gazebo_conversion_keeps_body_legs_and_sensors(self):
        urdf = subprocess.run(
            ['xacro', str(PKG / 'urdf/robot.urdf.xacro')],
            capture_output=True, text=True, check=True, timeout=30)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'robot.urdf'
            path.write_text(urdf.stdout)
            sdf = subprocess.run(['gz', 'sdf', '-p', str(path)],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(sdf.returncode, 0, sdf.stderr)
        model = ET.fromstring(sdf.stdout).find('model')
        links = {link.get('name') for link in model.findall('link')}
        self.assertIn('base_link', links, sdf.stderr)
        for leg in ('fr', 'fl', 'rr', 'rl'):
            self.assertIn(f'{leg}_calf_link', links)
        self.assertIsNotNone(model.find(".//sensor[@type='imu']"))
        self.assertIsNotNone(model.find(".//sensor[@type='gpu_lidar']"))

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
