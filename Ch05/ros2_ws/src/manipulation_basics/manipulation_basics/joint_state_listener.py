"""Monitor the configured Ch05 joint with safe JointState indexing."""

import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

from manipulation_basics.joint_state_validation import extract_joint_measurement


class JointStateListener(Node):
    """Log validated joint measurements at a bounded rate."""

    def __init__(self):
        super().__init__('joint_state_listener')
        self.declare_parameter('target_joint', 'joint2')
        self.declare_parameter('log_period_sec', 0.5)
        self.target_joint = self.get_parameter('target_joint').value
        self.log_period = float(self.get_parameter('log_period_sec').value)
        if self.log_period <= 0:
            raise ValueError('log_period_sec must be positive')
        self._last_log = -float('inf')
        self._last_warn = -float('inf')
        self.subscription = self.create_subscription(
            JointState, '/joint_states', self.listener_callback, 10)
        self.get_logger().info(f'Monitoring: {self.target_joint}')

    def listener_callback(self, msg):
        now = time.monotonic()
        result = extract_joint_measurement(
            msg.name, msg.position, msg.velocity, self.target_joint)
        if result is None:
            if now - self._last_warn >= 5.0:
                self.get_logger().warning('Joint missing or invalid position')
                self._last_warn = now
            return
        if now - self._last_log < self.log_period:
            return
        position, velocity = result
        velocity_text = (f'{velocity:.4f} rad/s' if velocity is not None
                         else 'N/A (not reported)')
        self.get_logger().info(
            f'Joint: {self.target_joint} | Pos: {position:.4f} rad '
            f'({math.degrees(position):.2f} deg) | Vel: {velocity_text}')
        self._last_log = now


def main(args=None):
    rclpy.init(args=args)
    node = JointStateListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
