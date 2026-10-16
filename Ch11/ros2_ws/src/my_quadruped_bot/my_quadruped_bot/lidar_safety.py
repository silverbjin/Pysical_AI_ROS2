"""11.3.4: obstacle warnings and explicit unknown/stale scan states.

This node never publishes cmd_vel. Its status is educational monitoring, not an
emergency-stop controller or a certification of collision-free motion.
"""
from dataclasses import asdict
import json
import math
import time

import rclpy
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from my_quadruped_bot.sensors.lidar_processing import analyze_front_sector, scan_is_fresh


class LidarSafety(Node):
    """Watch +/-30 degrees in the aligned lidar_link frame, warn below 0.5 m."""

    def __init__(self):
        super().__init__('lidar_safety')
        descriptor = ParameterDescriptor(read_only=True)
        self.safe_distance = self.declare_parameter('safe_distance', 0.5, descriptor).value
        self.scope_deg = self.declare_parameter('scope_deg', 30.0, descriptor).value
        self.scan_timeout = self.declare_parameter('scan_timeout', 0.5, descriptor).value
        self.expected_frame = self.declare_parameter('expected_frame', 'lidar_link', descriptor).value
        if not math.isfinite(self.scan_timeout) or self.scan_timeout <= 0:
            raise ValueError('scan_timeout must be finite and positive')
        # Validate configurable geometry before accepting any scan.
        analyze_front_sector([], 0.0, 0.01, 0.1, 10.0, self.safe_distance, self.scope_deg)
        qos = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                         history=QoSHistoryPolicy.KEEP_LAST, depth=5)
        self.subscription = self.create_subscription(LaserScan, '/scan', self.lidar_callback, qos)
        self.status_pub = self.create_publisher(String, '/lidar_safety/status', 10)
        self.last_stamp = None
        self.last_received = None
        self.last_state = None
        self.timer = self.create_timer(
            0.1, self.check_timeout, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info(
            f'LiDAR 전방 감시: 좌우 {self.scope_deg}도, 경고 거리 {self.safe_distance} m. '
            '이 노드는 정지 명령을 발행하지 않습니다.')

    def emit(self, state, reason, result=None):
        data = asdict(result) if result is not None else {
            'state': state, 'reason': reason, 'min_distance': None,
            'sector_count': 0, 'valid_count': 0, 'invalid_count': 0,
            'coverage_complete': False}
        data.update(state=state, reason=reason, safe_distance=self.safe_distance,
                    scope_deg=self.scope_deg, scan_stamp=self.last_stamp)
        output = String()
        output.data = json.dumps(data, allow_nan=False)
        self.status_pub.publish(output)
        if state == 'OBSTACLE':
            self.get_logger().warning(
                f'[충돌 위험] 전방 최소 거리 {data["min_distance"]:.2f} m '
                f'< {self.safe_distance:.2f} m', throttle_duration_sec=1.0)
        elif state != self.last_state:
            if state == 'CLEAR':
                self.get_logger().info('전방 유효 측정값이 경고 거리 밖에 있습니다.')
            else:
                self.get_logger().warning(f'LiDAR 판단 불가: {state} ({reason})')
        self.last_state = state

    def lidar_callback(self, msg):
        stamp = msg.header.stamp
        if stamp.sec < 0 or not 0 <= stamp.nanosec < 1_000_000_000:
            self.emit('UNKNOWN', 'invalid_stamp')
            return
        self.last_stamp = stamp.sec + stamp.nanosec/1e9
        self.last_received = time.monotonic()
        now = self.get_clock().now().nanoseconds/1e9
        if not scan_is_fresh(self.last_stamp, now, self.last_received,
                             time.monotonic(), self.scan_timeout):
            self.emit('STALE', 'acquisition_stamp_out_of_window')
            return
        if msg.header.frame_id != self.expected_frame:
            self.emit('UNKNOWN', 'unexpected_sensor_frame')
            return
        try:
            result = analyze_front_sector(
                msg.ranges, msg.angle_min, msg.angle_increment,
                msg.range_min, msg.range_max, self.safe_distance, self.scope_deg)
        except ValueError as error:
            self.emit('UNKNOWN', str(error))
            return
        self.emit(result.state, result.reason, result)

    def check_timeout(self):
        if not scan_is_fresh(self.last_stamp, self.get_clock().now().nanoseconds/1e9,
                             self.last_received, time.monotonic(), self.scan_timeout):
            self.emit('STALE', 'no_fresh_scan')


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = LidarSafety()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
