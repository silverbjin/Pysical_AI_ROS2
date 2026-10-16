"""ROS-independent regression tests for the Ch11 sensor contract."""
import ast
import importlib
import importlib.util
import math
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
import xml.etree.ElementTree as ET

import yaml

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


def sample(x=1.0):
    return NS(
        header=NS(stamp=NS(sec=2, nanosec=100), frame_id='odom'),
        child_frame_id='base_footprint',
        pose=NS(pose=NS(position=NS(x=x, y=2.0, z=0.3),
                        orientation=NS(x=0.0, y=0.0, z=0.0, w=1.0)),
                covariance=[0.0] * 36),
        twist=NS(twist=NS(linear=NS(x=0.2, y=0.0, z=0.0),
                          angular=NS(x=0.0, y=0.0, z=0.1)),
                 covariance=[0.0] * 36))


class ObservationTests(unittest.TestCase):
    def setUp(self):
        name = 'my_quadruped_bot.odometry_observation'
        self.assertIsNotNone(importlib.util.find_spec(name),
                             'Missing measured-odometry adapter core')
        self.adapt = importlib.import_module(name).adapt_observation

    def test_preserves_observed_motion_and_sensor_stamp(self):
        msg = sample(3.0)
        result = self.adapt(msg)
        self.assertEqual(result.pose.pose.position.x, 3.0)
        self.assertEqual(result.twist.twist.linear.x, 0.2)
        self.assertEqual(result.header.stamp.nanosec, 100)
        self.assertEqual(msg.pose.covariance, [0.0] * 36)

    def test_external_motion_is_not_command_integration(self):
        first, pushed = self.adapt(sample(0.0)), self.adapt(sample(0.7))
        self.assertAlmostEqual(pushed.pose.pose.position.x - first.pose.pose.position.x, 0.7)

    def test_covariance_is_positive_and_not_claimed_zero_error(self):
        result = self.adapt(sample())
        self.assertTrue(all(result.pose.covariance[i] > 0 for i in range(0, 36, 7)))
        self.assertTrue(all(result.twist.covariance[i] > 0 for i in range(0, 36, 7)))

    def test_rejects_wrong_frames(self):
        for field in ('parent', 'child'):
            msg = sample()
            if field == 'parent':
                msg.header.frame_id = 'world'
            else:
                msg.child_frame_id = 'unknown_body'
            with self.assertRaises(ValueError):
                self.adapt(msg)

    def test_rejects_nonfinite_pose_and_twist(self):
        for value in (math.nan, math.inf):
            with self.assertRaises(ValueError):
                self.adapt(sample(value))
            msg = sample()
            msg.twist.twist.angular.z = value
            with self.assertRaises(ValueError):
                self.adapt(msg)

    def test_rejects_invalid_quaternion(self):
        msg = sample()
        msg.pose.pose.orientation.w = 0.0
        with self.assertRaises(ValueError):
            self.adapt(msg)

    def test_rejects_invalid_stamp(self):
        msg = sample()
        msg.header.stamp.nanosec = 1000000000
        with self.assertRaises(ValueError):
            self.adapt(msg)

    def test_stream_drops_duplicates_and_latches_clock_reversal(self):
        module = importlib.import_module('my_quadruped_bot.odometry_observation')
        self.assertTrue(hasattr(module, 'ObservationStream'))
        stream = module.ObservationStream()
        self.assertIsNotNone(stream.accept(sample()))
        self.assertIsNone(stream.accept(sample()))
        older = sample()
        older.header.stamp.sec = 1
        with self.assertRaises(ValueError):
            stream.accept(older)
        newer = sample()
        newer.header.stamp.sec = 3
        with self.assertRaises(ValueError):
            stream.accept(newer)

    def test_invalid_sample_does_not_advance_stream_time(self):
        module = importlib.import_module('my_quadruped_bot.odometry_observation')
        self.assertTrue(hasattr(module, 'ObservationStream'))
        stream = module.ObservationStream()
        invalid = sample(math.nan)
        with self.assertRaises(ValueError):
            stream.accept(invalid)
        self.assertIsNotNone(stream.accept(sample()))


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.ekf = yaml.safe_load((PKG / 'config/ekf.yaml').read_text())['ekf_filter_node']['ros__parameters']
        self.bridge = yaml.safe_load((PKG / 'config/ros_gz_bridge.yaml').read_text())

    def test_imu_input_has_bridge_source(self):
        sources = {x['ros_topic_name'] for x in self.bridge if x['direction'] == 'GZ_TO_ROS'}
        self.assertIn(self.ekf['imu0'], sources)

    def test_imu_frame_is_explicit_physical_mount(self):
        root = ET.parse(PKG / 'urdf/common/gazebo_control.xacro').getroot()
        imu = root.find("./gazebo[@reference='base_link']/sensor[@type='imu']")
        self.assertIsNotNone(imu)
        bridge = next(x for x in self.bridge if x['ros_topic_name'] == '/imu/data_raw')
        self.assertEqual(bridge['frame_id'], 'base_link')

    def test_gazebo_measures_3d_pose_without_ros_tf_bridge(self):
        root = ET.parse(PKG / 'urdf/common/gazebo_control.xacro').getroot()
        plugin = root.find(".//plugin[@name='gz::sim::systems::OdometryPublisher']")
        self.assertIsNotNone(plugin, 'No physical observation source configured')
        self.assertEqual(plugin.findtext('dimensions'), '3')
        source = next(x for x in self.bridge if x['ros_topic_name'] == '/simulation/odom')
        self.assertEqual(source['gz_topic_name'], plugin.findtext('odom_topic'))
        self.assertFalse(any(x['ros_type_name'] == 'tf2_msgs/msg/TFMessage' for x in self.bridge))

    def test_fsm_is_not_an_odometry_or_tf_authority(self):
        tree = ast.parse((PKG / 'my_quadruped_bot/trot_controllerFSM.py').read_text())
        names = {x.id for x in ast.walk(tree) if isinstance(x, ast.Name)}
        self.assertNotIn('TransformBroadcaster', names)
        self.assertNotIn('Odometry', names)

    def test_ekf_does_not_double_count_pose_and_derived_velocity(self):
        self.assertTrue(self.ekf.get('use_sim_time', False))
        self.assertTrue(self.ekf['publish_tf'])
        self.assertEqual(len(self.ekf['odom0_config']), 15)
        self.assertFalse(any(self.ekf['odom0_config'][6:]))

    def test_active_launch_has_no_command_integrator(self):
        text = (PKG / 'launch/localization.launch.py').read_text()
        self.assertNotIn("executable='leg_odometry'", text)
        self.assertIn("executable='sim_odometry'", text)


if __name__ == '__main__':
    unittest.main()
