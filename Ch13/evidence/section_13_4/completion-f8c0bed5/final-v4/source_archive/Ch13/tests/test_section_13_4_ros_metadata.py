"""Observe the installed RMW metadata instead of assuming an upstream API shape."""
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String


def test_actual_message_info_fields():
    rclpy.init(domain_id=154)
    node = rclpy.create_node('message_info_probe')
    executor = SingleThreadedExecutor()
    received = []
    try:
        subscription = node.create_subscription(String, '/message_info_probe',
            lambda message, info: received.append(info), 10)
        publisher = node.create_publisher(String, '/message_info_probe', 10)
        timer = node.create_timer(.02, lambda: publisher.publish(String(data='metadata_only')))
        executor.add_node(node)
        deadline = time.monotonic()+2.
        while not received and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
        assert received
        print('INSTALLED_MESSAGE_INFO:', repr(received[0]))
        assert isinstance(received[0], dict)
        assert 'source_timestamp' in received[0] and 'received_timestamp' in received[0]
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()
