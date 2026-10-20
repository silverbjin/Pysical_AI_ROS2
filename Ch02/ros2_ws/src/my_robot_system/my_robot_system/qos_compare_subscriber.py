#!/usr/bin/env python3
"""Best-effort 발행자와 reliable/best-effort 구독자의 호환성을 비교한다."""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import String


class QosCompareSubscriber(Node):
    def __init__(self):
        super().__init__('qos_compare_subscriber')
        self.declare_parameter('reliability', 'reliable')
        mode = self.get_parameter('reliability').value
        if mode not in ('reliable', 'best_effort'):
            raise ValueError('reliability must be reliable or best_effort')
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=(ReliabilityPolicy.RELIABLE
                         if mode == 'reliable' else ReliabilityPolicy.BEST_EFFORT),
            durability=DurabilityPolicy.VOLATILE,
        )
        self.subscription = self.create_subscription(
            String, 'video_stream', self.on_message, qos)
        self.received_count = 0
        self.monitor_timer = self.create_timer(3.0, self.warn_if_no_frames)
        self.get_logger().info(f'Subscribing to video_stream with reliability={mode}')

    def on_message(self, msg):
        self.received_count += 1
        self.get_logger().info(f'Received frame: {msg.data}')

    def warn_if_no_frames(self):
        # 미수신 원인은 QoS 외에도 publisher 미기동일 수 있으므로 단정 금지.
        if self.received_count == 0:
            self.get_logger().warn(
                'No frames received: check publisher, topic type and offered/requested QoS.'
            )


def main(args=None):
    rclpy.init(args=args)
    node = QosCompareSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
