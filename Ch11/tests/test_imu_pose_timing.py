"""Exercise IMU visualization against real tf2 interpolation and missing data."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'))


@unittest.skipUnless(importlib.util.find_spec('rclpy'), 'Requires ROS Python and tf2')
class ImuPoseTimingTests(unittest.TestCase):
    def setUp(self):
        import rclpy
        from rclpy.parameter import Parameter
        from my_quadruped_bot.imu_pose_viz import ImuPoseViz

        rclpy.init(domain_id=92)
        self.node = ImuPoseViz()
        self.node.set_parameters([Parameter('use_sim_time', value=True)])
        self.logger = Mock()
        self.node.get_logger = lambda: self.logger
        # Record the real node's output without needing a DDS discovery delay.
        self.node.publisher = Mock()
        self.set_time(2.0)

    def tearDown(self):
        import rclpy
        self.node.destroy_node()
        rclpy.shutdown()

    def set_time(self, seconds):
        from rclpy.time import Time
        self.node.get_clock().set_ros_time_override(Time(seconds=seconds))

    def add_tf(self, seconds, x):
        from geometry_msgs.msg import TransformStamped
        from rclpy.time import Time
        tf = TransformStamped()
        tf.header.stamp = Time(seconds=seconds).to_msg()
        tf.header.frame_id = 'odom'
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x = x
        tf.transform.rotation.w = 1.0
        self.node.buffer.set_transform(tf, 'test')

    def add_imu(self, seconds):
        from rclpy.time import Time
        from sensor_msgs.msg import Imu
        imu = Imu()
        imu.header.stamp = Time(seconds=seconds).to_msg()
        imu.header.frame_id = 'base_link'
        imu.orientation.w = 1.0
        self.node.on_imu(imu)

    def test_brief_future_extrapolation_waits_then_interpolates_without_warning(self):
        self.add_tf(1.99, 1.0)
        self.add_imu(2.0)
        self.node.flush()
        self.node.publisher.publish.assert_not_called()
        self.logger.warning.assert_not_called()
        self.add_tf(2.01, 3.0)
        self.node.flush()
        pose = self.node.publisher.publish.call_args.args[0]
        self.assertEqual(pose.header.stamp.sec, 2)
        self.assertAlmostEqual(pose.pose.position.x, 2.0, delta=1e-6)
        self.assertEqual(pose.pose.orientation.w, 1.0)

    def test_missing_tf_warns_when_sample_expires_without_fabricating_pose(self):
        self.add_imu(2.0)
        self.node.flush()
        self.logger.warning.assert_not_called()
        self.set_time(2.6)
        self.node.flush()
        self.logger.warning.assert_called_once()
        self.node.publisher.publish.assert_not_called()
        self.assertFalse(self.node.pending)

    def test_old_sample_drop_does_not_warn_while_current_pose_flows(self):
        self.add_tf(1.99, 1.0)
        self.add_tf(2.01, 3.0)
        self.add_imu(2.0)
        self.node.flush()
        self.node.publisher.publish.assert_called_once()
        self.add_imu(1.0)
        self.node.flush()
        self.logger.warning.assert_not_called()

    def test_tf_outage_after_success_still_warns_and_does_not_reuse_old_pose(self):
        self.add_tf(1.99, 1.0)
        self.add_tf(2.01, 3.0)
        self.add_imu(2.0)
        self.node.flush()
        self.set_time(3.0)
        self.add_imu(3.0)
        self.node.flush()
        self.set_time(3.6)
        self.node.flush()
        self.logger.warning.assert_called_once()
        self.node.publisher.publish.assert_called_once()


if __name__ == '__main__':
    unittest.main()
