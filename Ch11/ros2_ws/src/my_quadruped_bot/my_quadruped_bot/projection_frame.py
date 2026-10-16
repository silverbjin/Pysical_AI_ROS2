"""Publish odom->scan_ground from measured EKF pose; never replace robot TF."""
import math
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rcl_interfaces.msg import ParameterDescriptor
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
from my_quadruped_bot.sensors.projection_frame import level_pose


class ProjectionFrame(Node):
    def __init__(self):
        super().__init__('projection_frame')
        self.declare_parameter('ground_height', 0.0, ParameterDescriptor(read_only=True))
        self.ground_height = self.get_parameter('ground_height').value
        if not math.isfinite(self.ground_height):
            raise ValueError('ground_height must be finite')
        self.broadcaster = TransformBroadcaster(self)
        self.last_stamp = None
        self.reset_required = False
        self.sub = self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)

    def on_odom(self, msg):
        if self.reset_required or (msg.header.frame_id, msg.child_frame_id) != ('odom', 'base_footprint'):
            return
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        if stamp <= 0 or stamp == self.last_stamp:
            return
        if self.last_stamp is not None and stamp < self.last_stamp:
            self.reset_required = True
            self.get_logger().error('Time reversed: restart the complete simulation and SLAM session.')
            return
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        try:
            xyz, xyzw = level_pose((p.x,p.y,p.z), (q.x,q.y,q.z,q.w), self.ground_height)
        except ValueError:
            return
        self.last_stamp = stamp
        tf = TransformStamped()
        tf.header = msg.header
        tf.child_frame_id = 'scan_ground'
        tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = xyz
        tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z, tf.transform.rotation.w = xyzw
        self.broadcaster.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ProjectionFrame()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
