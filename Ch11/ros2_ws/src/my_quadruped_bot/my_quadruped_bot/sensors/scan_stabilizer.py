"""11.6 IMU scan gate: nearest acquisition-time orientation plus mounting TF."""
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Imu
from tf2_ros import TransformException
from my_quadruped_bot.slam_scan_filter import SlamScanFilter
from my_quadruped_bot.sensors.attitude_history import AttitudeHistory, multiply


class ScanStabilizer(SlamScanFilter):
    def __init__(self):
        super().__init__(node_name='scan_stabilizer', output_default='/scan_stabilized')
        desc = ParameterDescriptor(read_only=True)
        self.declare_parameter('imu_topic', '/imu/data_raw', desc)
        self.declare_parameter('imu_frame', 'base_link', desc)
        self.declare_parameter('max_imu_delta', .03, desc)
        self.imu_frame = self.get_parameter('imu_frame').value
        self.history = AttitudeHistory(self.get_parameter('max_imu_delta').value)
        self.imu_sub = self.create_subscription(Imu, self.get_parameter('imu_topic').value,
                                                self.on_imu, qos_profile_sensor_data)

    def on_imu(self, msg):
        q = msg.orientation
        available = msg.orientation_covariance[0] != -1 and msg.header.frame_id == self.imu_frame
        self.history.add(self.stamp_ns(msg), (q.x, q.y, q.z, q.w), available)
        self.flush()

    def rotation_at(self, msg):
        imu_q = self.history.nearest(self.stamp_ns(msg))
        if imu_q is None:
            return None
        try:
            tf = self.buffer.lookup_transform(self.imu_frame, msg.header.frame_id,
                                              Time.from_msg(msg.header.stamp))
            q = tf.transform.rotation
            return multiply(imu_q, (q.x, q.y, q.z, q.w))
        except (TransformException, ValueError):
            return None


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ScanStabilizer()
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
