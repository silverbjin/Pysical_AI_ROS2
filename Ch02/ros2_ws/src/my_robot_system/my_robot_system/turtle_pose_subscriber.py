#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose  # Turtlesim 전용 위치 메시지 타입

class TurtlePoseSubscriber(Node):
    def __init__(self):
        super().__init__('turtle_pose_subscriber')
        
        # 1. 서브스크라이버 생성
        # self.create_subscription(메시지타입, '토픽이름', 콜백함수, 큐사이즈)
        self.subscription = self.create_subscription(
            Pose,
            '/turtle1/pose',
            self.listener_callback,
            10)
        
        # 사용하지 않는 변수 경고를 방지하기 위한 더미 코드 (선택사항)
        self.subscription 

        self.get_logger().info('Turtle Pose Subscriber Started')

    def listener_callback(self, msg):
        """
        토픽에 새로운 데이터가 도착할 때마다 호출되는 콜백 함수
        msg: 수신된 데이터 패킷
        """
        # 수신된 위치 정보를 로그로 출력
        # msg.x, msg.y, msg.theta 등은 turtlesim/msg/Pose 정의를 따른다.
        self.get_logger().info(f'Received Pose: X={msg.x:.2f}, Y={msg.y:.2f}, Theta={msg.theta:.2f}')
        
        # [실무 팁] 
        # 서브스크라이버 콜백 함수는 최대한 가볍게 유지해야 한다.
        # 여기서 복잡한 연산(예: 딥러닝 추론)을 수행하면 
        # 다음 들어오는 데이터가 밀리거나 유실될 수 있다.

def main(args=None):
    rclpy.init(args=args)
    node = TurtlePoseSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
