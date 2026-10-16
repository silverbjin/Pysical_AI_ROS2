#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist  # 로봇 속도 제어를 위한 메시지 타입

class TurtleCmdPublisher(Node):
    def __init__(self):
        # 1. 노드 이름 초기화 ('turtle_cmd_publisher')
        super().__init__('turtle_cmd_publisher')
        
        # 2. 퍼블리셔 생성
        # self.create_publisher(메시지타입, '토픽이름', 큐사이즈)
        # 큐(Queue) 사이즈 10: 통신 상태가 나빠 데이터가 밀릴 경우, 최근 10개까지만 보관하고 
        # 오래된 것은 버리겠다는 뜻이다. (QoS의 기본 개념)
        self.publisher_ = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        
        # 3. 타이머 설정 (0.5초마다 timer_callback 실행)
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        self.get_logger().info('Turtle Cmd Publisher Started')

    def timer_callback(self):
        """
        주기적으로 실행되며 속도 명령을 발행하는 함수
        """
        msg = Twist()
        
        # 선속도(Linear Velocity): 로봇의 앞뒤 움직임 (m/s)
        msg.linear.x = 2.0 
        msg.linear.y = 0.0
        msg.linear.z = 0.0
        
        # 각속도(Angular Velocity): 로봇의 회전 움직임 (rad/s)
        # z축을 기준으로 1.0 rad/s 속도로 회전
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = 1.0
        
        # 4. 토픽 발행 (Publish)
        # 생성한 메시지 객체를 토픽에 실어 보낸다.
        self.publisher_.publish(msg)
        
        # 디버깅을 위해 로그 출력
        self.get_logger().info(f'Publishing: Linear X={msg.linear.x}, Angular Z={msg.angular.z}')

def main(args=None):
    rclpy.init(args=args)
    node = TurtleCmdPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
