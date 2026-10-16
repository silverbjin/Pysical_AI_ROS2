"""11.4 teaching input: cmd_vel-derived odometry, NOT measured leg motion."""
import math
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rcl_interfaces.msg import ParameterDescriptor
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

from my_quadruped_bot.localization.lab_math import CommandOdometry


class LegOdometry(Node):
    def __init__(self):
        super().__init__('leg_odometry')
        descriptor = ParameterDescriptor(read_only=True)
        defaults = {'scale': 0.9, 'noise_stddev': 0.01,
                    'angular_noise_stddev': 0.005, 'timeout': 0.3,
                    'max_dt': 0.2, 'seed': 42}
        options = {key: self.declare_parameter(key, value, descriptor).value
                   for key, value in defaults.items()}
        self.model = CommandOdometry(**options)
        self.subscription = self.create_subscription(Twist, '/cmd_vel', self.on_command, 10)
        self.publisher = self.create_publisher(Odometry, '/ekf_lab/raw', 10)
        self.timer = self.create_timer(0.02, self.update_odometry)
        self.get_logger().warning(
            '교육용 명령 적분 오도메트리입니다. 관절·접촉을 측정하지 않으며 '
            'scale/noise는 Gazebo의 실제 마찰을 바꾸지 않습니다.')

    def on_command(self, message):
        try:
            self.model.set_command(message.linear.x, message.linear.y, message.angular.z,
                                   self.get_clock().now().nanoseconds)
        except ValueError as error:
            self.get_logger().warning(str(error), throttle_duration_sec=5.0)

    def update_odometry(self):
        now = self.get_clock().now()
        if self.model.last_stamp is not None:
            dt = (now.nanoseconds-self.model.last_stamp)/1e9
            if dt < 0 or dt > self.model.max_dt:
                self.get_logger().warning(
                    '시각 역행/점프: 모의 포즈·명령을 초기화합니다. 비교 실험을 재시작하세요.',
                    throttle_duration_sec=5.0)
        state = self.model.step(now.nanoseconds)
        msg = Odometry()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_footprint'
        msg.pose.pose.position.x = state.x
        msg.pose.pose.position.y = state.y
        msg.pose.pose.orientation.z = math.sin(state.yaw/2)
        msg.pose.pose.orientation.w = math.cos(state.yaw/2)
        msg.twist.twist.linear.x = state.vx
        msg.twist.twist.linear.y = state.vy
        msg.twist.twist.angular.z = state.wz
        # Teaching assumptions, not sensor-calibrated confidence intervals.
        for i in range(0, 36, 7):
            msg.pose.covariance[i] = 1.0
            msg.twist.covariance[i] = 1.0
        for i in (0, 7, 35):
            msg.pose.covariance[i] = 0.05 + 0.002*self.model.elapsed
            msg.twist.covariance[i] = 0.04
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = LegOdometry()
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
