#!/usr/bin/env python3
"""Observe a real ROS graph; optionally exercise a SIMULATION with low velocity.

Exit 0 means only the checks listed in runtime.json passed. It is not a general
navigation, push-recovery or real-hardware safety certification.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.parameter import Parameter
from rclpy.time import Time
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, LaserScan
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener


def stamp_seconds(stamp):
    return stamp.sec + stamp.nanosec / 1e9


class Probe(Node):
    def __init__(self):
        super().__init__('ch11_runtime_probe',
                         parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.samples = defaultdict(list)
        self.received = {}
        self.tf_authors = set()
        self.tf_parents = set()
        self.clock = None
        self.errors = set()
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.subs = []
        for topic, kind in (
            ('/simulation/odom', Odometry), ('/odom/raw', Odometry),
            ('/odom', Odometry), ('/imu/data_raw', Imu), ('/scan', LaserScan)
        ):
            self.subs.append(self.create_subscription(
                kind, topic, self.callback_for(topic), qos_profile_sensor_data))
        self.subs.append(self.create_subscription(Clock, '/clock', self.on_clock, 10))
        self.subs.append(self.create_subscription(TFMessage, '/tf', self.on_tf, 100))

    def callback_for(self, topic):
        def callback(message):
            self.samples[topic].append(message)
            self.received[topic] = time.monotonic()
            if len(self.samples[topic]) > 5000:
                self.samples[topic].pop(0)
        return callback

    def on_clock(self, message):
        value = stamp_seconds(message.clock)
        if self.clock is not None and value < self.clock:
            self.errors.add('clock_reversed')
        self.clock = value

    def on_tf(self, message, info):
        for tf in message.transforms:
            if tf.child_frame_id == 'base_footprint':
                self.tf_parents.add(tf.header.frame_id)
                if tf.header.frame_id == 'odom':
                    self.tf_authors.add(bytes(info.publisher_gid).hex())

    def zero(self):
        self.cmd.publish(Twist())

    def upright(self):
        items = self.samples['/simulation/odom']
        if not items:
            return False
        p = items[-1].pose.pose
        q = p.orientation
        # z component of the body's up vector in world coordinates.
        up = 1.0 - 2.0 * (q.x*q.x + q.y*q.y)
        return p.position.z > 0.10 and up > math.cos(0.6)

    def ready(self):
        return self.clock is not None and all(
            len(self.samples[t]) >= 10 for t in
            ('/simulation/odom', '/odom/raw', '/odom', '/imu/data_raw', '/scan'))

    def report(self):
        checks = {}
        now = time.monotonic()
        for topic in ('/simulation/odom', '/odom/raw', '/odom', '/imu/data_raw', '/scan'):
            items = self.samples[topic]
            checks[topic + ':received'] = len(items) >= 10
            checks[topic + ':fresh'] = now - self.received.get(topic, 0) < 5.0
            stamps = [stamp_seconds(x.header.stamp) for x in items]
            checks[topic + ':monotonic'] = bool(stamps) and all(
                b >= a for a, b in zip(stamps, stamps[1:]))
            checks[topic + ':sim_clock'] = bool(stamps) and self.clock is not None and (
                abs(stamps[-1] - self.clock) < 1.0)
        checks['imu_frame'] = bool(self.samples['/imu/data_raw']) and all(
            m.header.frame_id == 'base_link' for m in self.samples['/imu/data_raw'])
        checks['scan_frame'] = bool(self.samples['/scan']) and all(
            m.header.frame_id == 'lidar_link' for m in self.samples['/scan'])
        imu_items = self.samples['/imu/data_raw']
        checks['imu_orientation_usable'] = bool(imu_items) and all(
            m.orientation_covariance[0] != -1.0 and
            all(math.isfinite(v) for v in (m.orientation.x, m.orientation.y,
                                           m.orientation.z, m.orientation.w)) and
            abs(sum(v*v for v in (m.orientation.x, m.orientation.y,
                                  m.orientation.z, m.orientation.w))-1.0) < 0.01
            for m in imu_items)
        scan_items = self.samples['/scan']
        checks['scan_samples_and_limits'] = bool(scan_items) and all(
            len(m.ranges) == 360 and m.angle_increment > 0 and
            abs(m.range_min-0.1) < 0.001 and abs(m.range_max-10.0) < 0.001
            for m in scan_items)
        for topic, owner in (('/odom', 'ekf_filter_node'), ('/odom/raw', 'sim_odometry')):
            publishers = self.get_publishers_info_by_topic(topic)
            checks[topic + ':single_owner'] = len(publishers) == 1 and publishers[0].node_name == owner
        checks['ekf_subscribes_actual_imu'] = any(
            x.node_name == 'ekf_filter_node'
            for x in self.get_subscriptions_info_by_topic('/imu/data_raw'))
        checks['one_tf_authority'] = len(self.tf_authors) == 1
        checks['one_base_parent'] = self.tf_parents == {'odom'}
        for parent, child in (('odom', 'base_footprint'), ('base_footprint', 'base_link'),
                              ('base_footprint', 'lidar_link')):
            checks[parent + '->' + child] = self.buffer.can_transform(parent, child, Time())
        observed = {stamp_seconds(m.header.stamp): m for m in self.samples['/simulation/odom']}
        pairs = [(observed[stamp_seconds(m.header.stamp)], m)
                 for m in self.samples['/odom/raw'] if stamp_seconds(m.header.stamp) in observed]
        checks['sensor_stamp_and_pose_preserved'] = len(pairs) >= 10 and all(
            all(abs(getattr(a.pose.pose.position, axis)-getattr(b.pose.pose.position, axis)) < 1e-9
                for axis in ('x', 'y', 'z')) for a, b in pairs)
        for topic in ('/simulation/odom', '/odom/raw', '/odom'):
            items = self.samples[topic]
            checks[topic + ':finite'] = bool(items) and all(
                all(math.isfinite(getattr(v, axis))
                    for v in (m.pose.pose.position, m.twist.twist.linear, m.twist.twist.angular)
                    for axis in ('x', 'y', 'z')) for m in items)
        checks['upright_at_end'] = self.upright()
        checks['no_probe_errors'] = not self.errors
        return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--motion', action='store_true',
                        help='Send 0.03 m/s for 3 simulation seconds, then zero.')
    args = parser.parse_args()
    rclpy.init()
    node = Probe()
    start_wall = time.monotonic()
    origin = None
    motion_start = None
    motion_end = None
    checks = {}
    try:
        while time.monotonic() - start_wall < 120:
            rclpy.spin_once(node, timeout_sec=0.05)
            if node.clock is None:
                continue
            if origin is None and node.ready():
                origin = node.clock
            if origin is None:
                continue
            elapsed = node.clock - origin
            if args.motion:
                others = [x for x in node.get_publishers_info_by_topic('/cmd_vel')
                          if x.node_name != node.get_name()]
                if others:
                    node.errors.add('competing_cmd_vel_publisher')
                    break
                if 5 <= elapsed < 8:
                    if not node.upright():
                        node.errors.add('unsafe_pose_before_or_during_motion')
                        break
                    if motion_start is None:
                        p = node.samples['/simulation/odom'][-1].pose.pose.position
                        motion_start = (p.x, p.y)
                    cmd = Twist()
                    cmd.linear.x = 0.03
                    node.cmd.publish(cmd)
                else:
                    node.zero()
                if elapsed >= 8 and motion_start is not None and motion_end is None:
                    p = node.samples['/simulation/odom'][-1].pose.pose.position
                    motion_end = (p.x, p.y)
            if elapsed >= 14:
                break
        checks = node.report()
        checks['completed_14_sim_seconds'] = origin is not None and node.clock-origin >= 14
        if args.motion:
            distance = (math.dist(motion_start, motion_end)
                        if motion_start is not None and motion_end is not None else 0.0)
            checks['physical_motion_over_5mm'] = distance > 0.005
            items = node.samples['/simulation/odom']
            tail = [m for m in items if node.clock is not None
                    and stamp_seconds(m.header.stamp) >= node.clock-1.0]
            checks['settled_after_zero'] = len(tail) >= 5 and all(
                math.hypot(m.twist.twist.linear.x, m.twist.twist.linear.y) < 0.05
                for m in tail)
    except Exception as error:
        node.errors.add(repr(error))
        checks['probe_exception_free'] = False
    finally:
        if args.motion:
            for _ in range(10):
                node.zero()
                rclpy.spin_once(node, timeout_sec=0.05)
        report = {
            'status': 'PASS' if checks and all(checks.values()) else 'FAIL',
            'scope': 'ROS graph + short simulation motion' if args.motion else 'ROS graph observation',
            'checks': checks,
            'counts': {k: len(v) for k, v in node.samples.items()},
            'errors': sorted(node.errors),
            'tf_authority_gids': sorted(node.tf_authors),
            'limitations': ['No SLAM/Nav2, push recovery, sensor accuracy or hardware acceptance.'],
        }
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        node.destroy_node()
        rclpy.shutdown()
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
