"""Forward engine observations, never integrate commands into synthetic odometry."""
from copy import deepcopy
import math

from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def make_odometry(pose, twist, stamp):
    values = [pose.position.x, pose.position.y, pose.position.z,
              pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w,
              twist.linear.x, twist.linear.y, twist.linear.z,
              twist.angular.x, twist.angular.y, twist.angular.z]
    if (stamp.sec * 1_000_000_000 + stamp.nanosec <= 0
            or not all(math.isfinite(v) for v in values)
            or abs(sum(v*v for v in values[3:7])-1) > 1e-5):
        raise ValueError('invalid native state/time/orientation')
    msg = Odometry()
    msg.header.stamp = deepcopy(stamp)
    msg.header.frame_id, msg.child_frame_id = 'odom', 'base_footprint'
    # base_footprint_joint is identity in this chapter, including z/roll/pitch.
    # This name is not a promise of a projected, planar footprint.
    msg.pose.pose, msg.twist.twist = deepcopy(pose), deepcopy(twist)
    return msg


class NativePoseAdapter(Node):
    def __init__(self):
        super().__init__('native_pose_adapter')
        engine = self.declare_parameter('engine', 'gazebo').value
        self.pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf = TransformBroadcaster(self)
        if engine == 'gazebo':
            self.sub = self.create_subscription(Odometry, '/native/odom', self.gazebo, 10)
        elif engine == 'mujoco':
            from mujoco_ros2_control_msgs.msg import FreeJointStateArray
            self.sub = self.create_subscription(FreeJointStateArray, '/native/free_joint_states', self.mujoco, 10)
        else:
            raise ValueError('unknown engine')

    def gazebo(self, msg):
        self.publish(msg.pose.pose, msg.twist.twist, msg.header.stamp)

    def mujoco(self, msg):
        states = [v for v in msg.free_joints if v.name == 'base_link']
        if len(states) == 1 and states[0].pose.header.frame_id == '':
            self.publish(states[0].pose.pose, states[0].twist.twist, states[0].pose.header.stamp)

    def publish(self, pose, twist, stamp):
        try:
            msg = make_odometry(pose, twist, stamp)
        except ValueError as exc:
            self.get_logger().warning(str(exc))
            return
        transform = TransformStamped()
        transform.header, transform.child_frame_id = msg.header, msg.child_frame_id
        transform.transform.translation.x = pose.position.x
        transform.transform.translation.y = pose.position.y
        transform.transform.translation.z = pose.position.z
        transform.transform.rotation = deepcopy(pose.orientation)
        self.tf.sendTransform(transform)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = NativePoseAdapter()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
