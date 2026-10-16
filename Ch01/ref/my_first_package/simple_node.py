#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class SimpleNode(Node):
    """
    1.6절 실습: 기본적인 타이머 기반 로깅 노드
    """
    def __init__(self):
        # 노드 이름을 'simple_node'로 초기화
        super().__init__('simple_node')
        
        # 1초마다 'timer_callback'을 실행하는 타이머 생성
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.counter = 0
        self.get_logger().info('Simple Node가 성공적으로 시작되었습니다.')

    def timer_callback(self):
        self.counter += 1
        # 터미널에 정보를 출력 (INFO 레벨)
        self.get_logger().info(f'ROS 2 Jazzy 실행 중... 카운트: {self.counter}')

def main(args=None):
    # 통신 초기화
    rclpy.init(args=args)
    # 노드 생성
    node = SimpleNode()
    try:
        # 노드 실행 (이벤트 루프)
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자에 의해 노드가 종료되었습니다.')
    finally:
        # 자원 해제
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()