#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image

class SimpleImageSubscriber(Node):
    def __init__(self):
        super().__init__('simple_image_subscriber')
        
        # [QoS 설정]
        # 센서 데이터(특히 이미지)는 'Best Effort'로 보내는 경우가 많다.
        # 따라서 수신측도 'Best Effort'로 맞춰야 호환성 문제가 생기지 않는다.
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # 서브스크라이버 생성
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.listener_callback,
            qos_profile
        )
        self.get_logger().info('이미지 수신 대기 중...')

    def listener_callback(self, msg):
        # 메시지 수신 시 호출되는 콜백 함수
        self.get_logger().info(
            f'이미지 수신 성공! 크기: {msg.width}x{msg.height}, 인코딩: {msg.encoding}'
        )
        # 여기서 msg.data는 1차원 바이트 배열(raw bytes)이다.
        # 다음 절에서 이를 OpenCV 이미지로 변환할 것이다.

def main(args=None):
    rclpy.init(args=args)
    node = SimpleImageSubscriber()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
