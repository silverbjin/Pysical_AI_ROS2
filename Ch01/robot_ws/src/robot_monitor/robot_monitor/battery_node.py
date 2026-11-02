#!/usr/bin/env python3
"""가상 배터리 값을 로깅하는 교육용 ROS 2 노드 (실제 센서 아님)."""
import rclpy
from rclpy.node import Node


class BatteryNode(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        self.battery_state = 100
        self.finished = False
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info('--- 모의 배터리 모니터링 시작 ---')

    def timer_callback(self):
        self.battery_state = max(0, self.battery_state - 10)
        msg = f'현재 모의 배터리 잔량: {self.battery_state}%'
        if self.battery_state > 60:
            self.get_logger().info(f'[정상] {msg}')
        elif self.battery_state > 20:
            self.get_logger().warn(f'[주의] {msg}')
        else:
            self.get_logger().error(f'[위험] {msg}')

        if self.battery_state == 0:
            self.get_logger().fatal('모의 배터리 0%: 실습 노드를 종료합니다.')
            self.timer.cancel()
            self.finished = True


def main(args=None):
    rclpy.init(args=args)
    node = BatteryNode()
    try:
        # 타이머 취소 후 rclpy.spin()에 계속 머무르지 않고 종료한다.
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
