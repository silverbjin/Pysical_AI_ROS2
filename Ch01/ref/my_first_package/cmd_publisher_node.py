#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
# 1.7절 의존성 관리: Twist 메시지 타입을 가져옴 (로봇 속도 제어용 표준)
from geometry_msgs.msg import Twist

class CmdPublisherNode(Node):
    """
    1.7절 실습: 시뮬레이션 환경의 로봇에게 속도 명령(Twist)을 발행하는 노드
    """
    def __init__(self):
        super().__init__('cmd_publisher_node')
        
        # 'cmd_vel' 토픽으로 Twist 메시지를 발행하는 Publisher 생성
        # 10은 큐(Queue) 사이즈를 의미함
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # 0.5초마다 실행 (2Hz)
        self.timer = self.create_timer(0.5, self.publish_velocity)
        self.get_logger().info('속도 명령 발행을 시작합니다.')

    def publish_velocity(self):
        msg = Twist()
        # 선속도 x축 방향으로 0.2m/s (전진)
        msg.linear.x = 0.2
        # 각속도 z축 방향으로 0.5rad/s (좌회전)
        msg.angular.z = 0.5
        
        self.publisher_.publish(msg)
        self.get_logger().info(f'명령 송신: v={msg.linear.x}, w={msg.angular.z}')

def main(args=None):
    rclpy.init(args=args)
    node = CmdPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()