#!/usr/bin/env python3
"""Synthetic LaserScan input on /lab/scan only; sends no robot commands."""
import argparse
import math

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanDemo(Node):
    def __init__(self, case):
        super().__init__('lidar_scan_demo')
        self.case = case
        self.publisher = self.create_publisher(LaserScan, '/lab/scan', qos_profile_sensor_data)
        self.timer = self.create_timer(0.1, self.publish_scan)
        self.get_logger().info(f'SYNTHETIC /lab/scan case={case}; Ctrl+C stops input.')

    def publish_scan(self):
        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = 'lidar_link'
        scan.angle_min = -math.pi
        scan.angle_increment = math.pi/180
        scan.angle_max = math.pi
        scan.range_min = 0.1
        scan.range_max = 10.0
        scan.scan_time = 0.1
        scan.ranges = [2.0]*361
        if self.case == 'obstacle':
            scan.ranges[180] = 0.3
        elif self.case == 'rear':
            scan.ranges[0] = 0.2
        elif self.case == 'invalid':
            scan.ranges = [math.inf]*361
        elif self.case == 'out_of_range':
            scan.ranges[180] = 20.0
        elif self.case == 'partial':
            scan.angle_min = -math.radians(5)
            scan.angle_max = math.radians(5)
            scan.ranges = [2.0]*11
        self.publisher.publish(scan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=(
        'clear', 'obstacle', 'rear', 'invalid', 'out_of_range', 'partial'), default='obstacle')
    args = parser.parse_args()
    rclpy.init(args=[])
    node = None
    try:
        node = ScanDemo(args.case)
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
