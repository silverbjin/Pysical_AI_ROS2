#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from std_msgs.msg import String

class QosTestNode(Node):
    def __init__(self):
        super().__init__('qos_test_node')

        # 1. 커스텀 QoS 프로파일 정의
        # 영상 전송용: 빠르고(BestEffort), 최신 데이터 1개만(KeepLast 1), 저장 안 함(Volatile)
        video_qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.VOLATILE
        )

        # 2. 퍼블리셔 생성 (Best Effort)
        self.publisher_ = self.create_publisher(
            String, 
            'video_stream', 
            qos_profile=video_qos_profile
        )

        # 3. 서브스크라이버 생성 (Reliable - 일부러 호환성 실패 유도)
        # 기본값인 10을 넣으면 내부적으로 Reliable로 설정된다.
        # self.subscriber_ = self.create_subscription(...) 
        
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        msg = String()
        msg.data = 'Frame Data'
        self.publisher_.publish(msg)
        self.get_logger().info('Published video frame (Best Effort)')

def main(args=None):
    rclpy.init(args=args)
    node = QosTestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
