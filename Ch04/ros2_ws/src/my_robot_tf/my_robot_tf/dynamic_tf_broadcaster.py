"""4.3절: 실제 ROS 시간 간격에 비례하는 동적 TF 방송."""

import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

from .trajectory_math import circle_pose, yaw_quaternion


class DynamicFramePublisher(Node):
    def __init__(self):
        super().__init__("dynamic_tf_broadcaster_node")
        self.tf_broadcaster = TransformBroadcaster(self)
        self.radius = 2.0
        self.angular_speed = 1.5  # rad/s: 콜백 지연 시에도 목표 각속도를 유지
        self.theta = 0.0
        self.last_time_ns = self.get_clock().now().nanoseconds
        self.timer = self.create_timer(1.0 / 30.0, self.broadcast_timer_callback)
        self.get_logger().info("Dynamic TF broadcaster started (30 Hz nominal)")

    def broadcast_timer_callback(self):
        now = self.get_clock().now()
        now_ns = now.nanoseconds
        if now_ns < self.last_time_ns:
            # 시뮬레이터 /clock이 되감긴 경우 오래된 dt로 점프하지 않는다.
            self.last_time_ns = now_ns
            self.get_logger().warn("Clock moved backwards; reset motion timer")
            return

        dt = min((now_ns - self.last_time_ns) * 1e-9, 0.25)
        self.last_time_ns = now_ns
        self.theta = (self.theta + self.angular_speed * dt) % (2 * math.pi)

        x, y, yaw = circle_pose(self.radius, self.theta)
        qx, qy, qz, qw = yaw_quaternion(yaw)

        transform = TransformStamped()
        transform.header.stamp = now.to_msg()
        transform.header.frame_id = "world"
        transform.child_frame_id = "turtle_frame"
        transform.transform.translation.x = x
        transform.transform.translation.y = y
        transform.transform.translation.z = 0.0
        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(transform)


def main():
    rclpy.init()
    node = DynamicFramePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
