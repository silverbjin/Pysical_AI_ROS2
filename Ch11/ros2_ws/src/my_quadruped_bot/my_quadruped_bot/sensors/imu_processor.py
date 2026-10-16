"""11.2.4: fuse acceleration and angular velocity, ignoring input orientation."""
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray

from my_quadruped_bot.sensors.complementary_filter import ComplementaryFilter


class ImuProcessor(Node):
    """Publish [roll, pitch, yaw] in radians on the existing exercise topic."""

    def __init__(self):
        super().__init__('imu_processor')
        descriptor = ParameterDescriptor(read_only=True)
        alpha = self.declare_parameter('alpha', 0.98, descriptor).value
        max_dt = self.declare_parameter('max_dt', 0.2, descriptor).value
        self.filter = ComplementaryFilter(alpha=alpha, max_dt=max_dt)
        qos = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                         history=QoSHistoryPolicy.KEEP_LAST, depth=1)
        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.imu_callback, qos)
        self.rpy_pub = self.create_publisher(Float32MultiArray, '/imu/rpy_filtered', 10)
        self.get_logger().info(
            f'IMU complementary filter alpha={alpha}, max_dt={max_dt}s; '
            'input orientation ignored, dt from header.stamp')

    def imu_callback(self, msg):
        # -1 means that this measurement is not provided by the driver.
        if (msg.angular_velocity_covariance[0] == -1.0 or
                msg.linear_acceleration_covariance[0] == -1.0):
            self.get_logger().warning('Acceleration or gyro unavailable; sample dropped.',
                                      throttle_duration_sec=5.0)
            return
        stamp = msg.header.stamp
        if stamp.sec < 0 or not 0 <= stamp.nanosec < 1_000_000_000:
            self.get_logger().warning('Invalid IMU stamp; sample dropped.',
                                      throttle_duration_sec=5.0)
            return
        stamp_ns = stamp.sec*1_000_000_000 + stamp.nanosec
        a, g = msg.linear_acceleration, msg.angular_velocity
        previous_stamp = self.filter.last_stamp_ns
        try:
            rpy = self.filter.update(stamp_ns, (a.x, a.y, a.z), (g.x, g.y, g.z))
        except ValueError as error:
            self.get_logger().warning(str(error), throttle_duration_sec=5.0)
            return
        if rpy is None:
            return
        if previous_stamp is not None and (
                stamp_ns < previous_stamp or (stamp_ns-previous_stamp)/1e9 > self.filter.max_dt):
            self.get_logger().warning('Time reset/gap: roll/pitch reinitialized; yaw reset to zero.',
                                      throttle_duration_sec=5.0)
        output = Float32MultiArray()
        output.data = list(rpy)
        self.rpy_pub.publish(output)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ImuProcessor()
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
