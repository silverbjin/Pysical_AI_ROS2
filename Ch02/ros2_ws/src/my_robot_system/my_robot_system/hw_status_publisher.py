#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

# [중요] 우리가 만든 커스텀 메시지 모듈 임포트
# 패키지명.msg import 메시지파일명(클래스)
from my_robot_interfaces.msg import HardwareStatus

class HardwareStatusPublisher(Node):
    def __init__(self):
        super().__init__('hardware_status_publisher')
        
        # 커스텀 메시지 타입으로 퍼블리셔 생성
        self.pub = self.create_publisher(HardwareStatus, 'hardware_status', 10)
        
        self.timer = self.create_timer(1.0, self.publish_status)
        self.get_logger().info('Hardware Status Publisher Started')

    def publish_status(self):
        msg = HardwareStatus()
        msg.machine_id = 101
        msg.temperature_warning = False
        msg.debug_message = "All Systems Nominal"
        
        self.pub.publish(msg)
        self.get_logger().info(f'Published ID: {msg.machine_id}, Msg: {msg.debug_message}')

def main(args=None):
    rclpy.init(args=args)
    node = HardwareStatusPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
