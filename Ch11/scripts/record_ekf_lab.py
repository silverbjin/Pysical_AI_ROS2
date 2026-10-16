#!/usr/bin/env python3
"""Record actual ROS streams and pair by nearest stamp; never fabricate results."""
import argparse
import bisect
import csv
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=30.0,
                        help='Wall-clock recording duration')
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-delta', type=float, default=0.05,
                        help='Maximum pairing distance in simulation seconds')
    args = parser.parse_args()
    if args.seconds <= 0 or args.max_delta <= 0:
        parser.error('durations must be positive')
    rclpy.init(args=[])
    node = Node('ekf_lab_recorder')
    samples = {name: [] for name in ('raw', 'filtered', 'truth')}
    errors = []
    topics = {'raw': '/ekf_lab/raw', 'filtered': '/ekf_lab/filtered',
              'truth': '/simulation/odom'}

    def callback_for(name):
        def callback(msg):
            if (msg.header.frame_id, msg.child_frame_id) != ('odom', 'base_footprint'):
                errors.append('Unexpected frames: '+name)
                return
            t = msg.header.stamp.sec + msg.header.stamp.nanosec/1e9
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            values = (t, p.x, p.y, q.x, q.y, q.z, q.w)
            if not all(math.isfinite(v) for v in values):
                errors.append('Nonfinite data: '+name)
                return
            yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
            if samples[name] and t < samples[name][-1][0]:
                errors.append('Time reversal: '+name)
            samples[name].append((t, p.x, p.y, yaw))
        return callback

    subscriptions = [node.create_subscription(Odometry, topic, callback_for(name),
                                               qos_profile_sensor_data)
                     for name, topic in topics.items()]
    node.get_logger().info('Recording raw / filtered / Gazebo truth; no commands sent.')
    started = time.monotonic()
    try:
        while rclpy.ok() and time.monotonic()-started < args.seconds:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    # Keep the subscriptions alive throughout spin.
    del subscriptions

    times = {name: [s[0] for s in data] for name, data in samples.items()}

    def nearest(name, t):
        data = samples[name]
        if not data:
            return None
        i = bisect.bisect_left(times[name], t)
        candidates = [data[j] for j in (i-1, i) if 0 <= j < len(data)]
        best = min(candidates, key=lambda s: abs(s[0]-t))
        return best if abs(best[0]-t) <= args.max_delta else None

    pairs = []
    if not errors:
        for filtered in samples['filtered']:
            raw, truth = nearest('raw', filtered[0]), nearest('truth', filtered[0])
            if raw is not None and truth is not None:
                pairs.append((raw, filtered, truth))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {'topics': topics, 'counts': {k: len(v) for k, v in samples.items()},
                'paired_rows': len(pairs), 'max_delta_seconds': args.max_delta,
                'errors': sorted(set(errors)), 'synthetic_results': False,
                'alignment': 'each trajectory translated and rotated to its first paired pose',
                'scope': 'relative planar error; truth used only for evaluation'}
    output.with_suffix('.json').write_text(json.dumps(metadata, indent=2)+'\n')
    if len(pairs) < 5 or errors:
        print(json.dumps(metadata, indent=2))
        raise SystemExit('Not enough valid synchronized samples; no comparison CSV produced.')

    origins = pairs[0]

    def relative(sample, origin):
        dx, dy = sample[1]-origin[1], sample[2]-origin[2]
        c, s = math.cos(origin[3]), math.sin(origin[3])
        return c*dx+s*dy, -s*dx+c*dy

    fields = ('t', 'raw_x', 'raw_y', 'filtered_x', 'filtered_y', 'truth_x', 'truth_y',
              'raw_error', 'filtered_error', 'raw_delta_t', 'truth_delta_t')
    with output.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        for raw, filtered, truth in pairs:
            r = relative(raw, origins[0])
            f = relative(filtered, origins[1])
            g = relative(truth, origins[2])
            writer.writerow((filtered[0]-origins[1][0], *r, *f, *g,
                             math.dist(r, g), math.dist(f, g),
                             raw[0]-filtered[0], truth[0]-filtered[0]))
    print(json.dumps(metadata, indent=2))
    print(output)


if __name__ == '__main__':
    main()
