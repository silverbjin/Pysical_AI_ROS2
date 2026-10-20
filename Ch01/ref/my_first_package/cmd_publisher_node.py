#!/usr/bin/env python3
"""교육용 Twist 발행 노드: 기본 속도 0, 제한된 반복, 정지 명령."""
import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class CmdPublisherNode(Node):
    """1.7절: 2 Hz로 속도 명령을 발행하는 제한 시간 입문 예제."""

    def __init__(self):
        super().__init__('cmd_publisher_node')

        # 기본값은 정지. 움직임 시연은 ROS 매개변수로 명시적으로 요청한다.
        self.declare_parameter('linear_x', 0.0)
        self.declare_parameter('angular_z', 0.0)
        self.declare_parameter('publish_count', 10)

        self.linear_x = float(self.get_parameter('linear_x').value)
        self.angular_z = float(self.get_parameter('angular_z').value)
        self.max_publish_count = int(self.get_parameter('publish_count').value)
        if not math.isfinite(self.linear_x) or not math.isfinite(self.angular_z):
            raise ValueError('linear_x와 angular_z는 유한한 숫자여야 합니다.')
        if self.max_publish_count <= 0:
            raise ValueError('publish_count는 1 이상의 정수여야 합니다.')

        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)
        self.publish_count = 0
        self.finished = False
        self.timer = self.create_timer(0.5, self.publish_velocity)
        self.get_logger().info(
            f'Twist 발행 시작: v={self.linear_x}, w={self.angular_z}, '
            f'횟수={self.max_publish_count}'
        )

    def publish_velocity(self):
        if self.finished:
            return

        msg = Twist()
        msg.linear.x = self.linear_x
        msg.angular.z = self.angular_z
        self.publisher_.publish(msg)
        self.publish_count += 1
        self.get_logger().info(
            f'명령 송신 {self.publish_count}/{self.max_publish_count}: '
            f'v={msg.linear.x}, w={msg.angular.z}'
        )

        if self.publish_count >= self.max_publish_count:
            self.publish_stop()
            self.timer.cancel()
            self.finished = True
            self.get_logger().info('발행 횟수 완료: 정지 명령을 전송했습니다.')

    def publish_stop(self):
        # DDS 전송의 실제 수신을 보장하지는 않는다.
        self.publisher_.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = CmdPublisherNode()
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            if rclpy.ok():
                node.publish_stop()
                # 종료 직전 DDS 통신을 진행할 짧은 기회를 제공한다.
                rclpy.spin_once(node, timeout_sec=0.1)
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
