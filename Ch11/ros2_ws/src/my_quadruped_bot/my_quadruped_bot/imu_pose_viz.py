"""Show measured Gazebo IMU attitude as RViz Pose axes at the body origin."""
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Imu
from tf2_ros import Buffer, TransformListener, TransformException

from my_quadruped_bot.imu_visualization_math import pose_components


class ImuPoseViz(Node):
    """Use raw IMU orientation; wait briefly for timestamp-matched translation."""

    def __init__(self):
        super().__init__('imu_pose_viz')
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.publisher = self.create_publisher(PoseStamped, '/figure_11_2/imu_pose', 10)
        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.on_imu, qos_profile_sensor_data)
        self.pending = deque(maxlen=100)
        self.last_now = None
        self.timer = self.create_timer(0.03, self.flush)
        self.get_logger().info('IMU axes: /imu/data_raw -> /figure_11_2/imu_pose in odom')

    def on_imu(self, message):
        if message.header.frame_id != 'base_link':
            self.get_logger().warning(
                'Figure expects a base_link-aligned IMU; check gz_frame_id.',
                throttle_duration_sec=5.0)
            return
        try:
            q = message.orientation
            pose_components((q.x, q.y, q.z, q.w), (0, 0, 0),
                            message.orientation_covariance[0] != -1.0)
        except ValueError as error:
            self.get_logger().warning(str(error), throttle_duration_sec=5.0)
            return
        self.pending.append(message)

    def flush(self):
        now = self.get_clock().now().nanoseconds
        if self.last_now is not None and now < self.last_now:
            self.pending.clear()
        self.last_now = now
        latest = None
        while self.pending:
            message = self.pending[0]
            stamp = Time.from_msg(message.header.stamp)
            age = (now-stamp.nanoseconds)/1e9
            if age > 0.5 or age < -0.5:
                self.pending.popleft()
                continue
            try:
                transform = self.buffer.lookup_transform('odom', 'base_link', stamp)
            except TransformException:
                # Keep the sample until the EKF's next TF arrives, up to 0.5 s.
                self.get_logger().warning(
                    'Waiting for timestamp-matched odom -> base_link TF.',
                    throttle_duration_sec=5.0)
                break
            self.pending.popleft()
            q = message.orientation
            t = transform.transform.translation
            try:
                p, q = pose_components((q.x, q.y, q.z, q.w), (t.x, t.y, t.z))
            except ValueError:
                continue
            pose = PoseStamped()
            pose.header.stamp = message.header.stamp
            pose.header.frame_id = 'odom'
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = p
            (pose.pose.orientation.x, pose.pose.orientation.y,
             pose.pose.orientation.z, pose.pose.orientation.w) = q
            latest = pose
        if latest is not None:
            self.publisher.publish(latest)


def main(args=None):
    rclpy.init(args=args)
    node = ImuPoseViz()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
