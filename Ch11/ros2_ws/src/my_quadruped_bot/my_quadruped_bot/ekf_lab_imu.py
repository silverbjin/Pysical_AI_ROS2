"""Prepare Imu covariance assumptions for the isolated EKF lesson."""
from copy import deepcopy
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.executors import ExternalShutdownException
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Imu

from my_quadruped_bot.localization.lab_math import covariance3


class LabImu(Node):
    def __init__(self):
        super().__init__('ekf_lab_imu')
        self.require_orientation = self.declare_parameter(
            'require_orientation', False, ParameterDescriptor(read_only=True)).value
        self.publisher = self.create_publisher(Imu, '/ekf_lab/imu', 10)
        self.subscription = self.create_subscription(
            Imu, '/imu/data_raw', self.on_imu, qos_profile_sensor_data)
        self.get_logger().info('EKF 실습: covariance가 미상인 필드에 교육용 분산 가정을 적용합니다.')

    def on_imu(self, message):
        if message.header.frame_id != 'base_link':
            self.get_logger().warning('Expected base_link-aligned IMU.', throttle_duration_sec=5.0)
            return
        result = deepcopy(message)
        q = message.orientation
        orientation_valid = (message.orientation_covariance[0] != -1.0 and
                             all(math.isfinite(v) for v in (q.x, q.y, q.z, q.w)) and
                             abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1.0) < 0.01)
        if self.require_orientation and not orientation_valid:
            self.get_logger().warning('Gravity removal requires valid orientation; sample dropped.',
                                      throttle_duration_sec=5.0)
            return
        try:
            if not orientation_valid:
                result.orientation_covariance = [-1.0]+[0.0]*8
            else:
                result.orientation_covariance = covariance3(message.orientation_covariance, 0.01)
            result.angular_velocity_covariance = covariance3(message.angular_velocity_covariance, 0.0004)
            result.linear_acceleration_covariance = covariance3(message.linear_acceleration_covariance, 0.25)
        except ValueError as error:
            self.get_logger().warning(str(error), throttle_duration_sec=5.0)
            return
        self.publisher.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = LabImu()
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
