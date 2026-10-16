#!/usr/bin/env python3
"""Read-only runtime probe: map cells, acquisition-time TF and live scan counts."""
import argparse
import json
from pathlib import Path
import time


def map_summary(width, height, resolution, frame, data):
    cells = list(data)
    valid = (width > 0 and height > 0 and resolution > 0 and frame == 'map'
             and len(cells) == width*height and all(-1 <= v <= 100 for v in cells))
    return {'valid': valid, 'width': width, 'height': height, 'resolution': resolution,
            'frame': frame, 'known_cells': sum(v >= 0 for v in cells),
            'free_cells': sum(0 <= v <= 25 for v in cells),
            'occupied_cells': sum(v >= 65 for v in cells)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=20.0, help='Wall-clock observation duration')
    parser.add_argument('--output', type=Path, default=Path('/tmp/slam_mapping_runtime.json'))
    args = parser.parse_args()
    if not 0 < args.seconds <= 600:
        parser.error('--seconds must be between 0 and 600')
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
    from rclpy.time import Time
    from nav_msgs.msg import OccupancyGrid, Odometry
    from sensor_msgs.msg import LaserScan
    from tf2_ros import Buffer, TransformException, TransformListener

    rclpy.init()
    node = Node('check_slam_mapping', parameter_overrides=[Parameter('use_sim_time', value=True)])
    buf = Buffer(node=node)
    listener = TransformListener(buf, node)
    result = {'map_messages': 0, 'raw_scans': 0, 'slam_scans': 0, 'odom_messages': 0,
              'scan_time_tf': False, 'map_to_odom': False, 'map': None}
    last_scan = None

    def scan(msg, key):
        nonlocal last_scan
        result[key] += 1
        if key == 'slam_scans':
            last_scan = msg

    def odom(msg):
        if msg.header.frame_id == 'odom' and msg.child_frame_id == 'base_footprint':
            result['odom_messages'] += 1

    def map_cb(msg):
        result['map_messages'] += 1
        result['map'] = map_summary(msg.info.width, msg.info.height, msg.info.resolution,
                                    msg.header.frame_id, msg.data)

    map_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
    subscriptions = [
        node.create_subscription(OccupancyGrid, '/map', map_cb, map_qos),
        node.create_subscription(Odometry, '/odom', odom, qos_profile_sensor_data),
        node.create_subscription(LaserScan, '/scan', lambda m: scan(m, 'raw_scans'), qos_profile_sensor_data),
        node.create_subscription(LaserScan, '/scan/slam', lambda m: scan(m, 'slam_scans'), qos_profile_sensor_data),
    ]
    try:
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            try:
                buf.lookup_transform('map', 'odom', Time())
                result['map_to_odom'] = True
            except TransformException:
                pass
            if last_scan is not None:
                try:
                    buf.lookup_transform('odom', last_scan.header.frame_id,
                                         Time.from_msg(last_scan.header.stamp))
                    result['scan_time_tf'] = True
                except TransformException:
                    pass
        m = result['map'] or {}
        result['pass'] = bool(result['map_messages'] and result['raw_scans'] and result['slam_scans']
                              and result['odom_messages'] and result['scan_time_tf']
                              and result['map_to_odom'] and m.get('valid')
                              and m.get('free_cells', 0) and m.get('occupied_cells', 0))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 0 if result['pass'] else 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
