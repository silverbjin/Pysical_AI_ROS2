#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node


class SimpleController(Node):
    """1초마다 Heartbeat을 ROS 로거에 기록하는 교육용 노드.

    주의: 이 노드는 토픽 Publisher를 생성하지 않는다.
    """

    def __init__(self):
        super().__init__('my_robot_node')
        self.get_logger().info('Simple Controller 노드가 시작되었습니다!')
        self.timer_period = 1.0
        self.counter = 0
        self.timer = self.create_timer(self.timer_period, self.timer_callback)

    def timer_callback(self):
        self.counter += 1
        self.get_logger().info(
            f'로봇 생존 신호 송신 중... (Heartbeat: {self.counter})'
        )


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = SimpleController()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info('종료 신호를 받았습니다.')
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
