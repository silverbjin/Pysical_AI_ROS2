"""Read-only standing and sensor probe; run in a sourced ROS environment."""
import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, LaserScan, JointState
from tf2_ros import Buffer, TransformListener

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--duration', type=float, default=30)
args = parser.parse_args()
rclpy.init()
node = Node('figure_11_2_repeat_probe')
buffer = Buffer()
listener = TransformListener(buffer, node)
counts = Counter()
samples = []
scan = {}
subs = []
last_received = {}

def receive(kind, msg):
    counts[kind] += 1
    last_received[kind] = time.monotonic()
    if kind == 'truth':
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
        if stamp >= 8:
            pose = msg.pose.pose
            q = pose.orientation
            up = max(-1.0, min(1.0, 1 - 2 * (q.x*q.x + q.y*q.y)))
            samples.append((stamp, pose.position.z, math.degrees(math.acos(up)),
                            pose.position.x, pose.position.y))
    if kind == 'scan':
        valid = [x for x in msg.ranges
                 if math.isfinite(x) and msg.range_min <= x <= msg.range_max]
        scan.update(frame=msg.header.frame_id, rays=len(msg.ranges),
                    finite_returns=len(valid), minimum=min(valid) if valid else None,
                    maximum=max(valid) if valid else None)

for kind, topic, cls in [('truth', '/simulation/odom', Odometry),
                         ('odom', '/odom', Odometry),
                         ('imu', '/imu/data_raw', Imu),
                         ('pose', '/figure_11_2/imu_pose', PoseStamped),
                         ('joints', '/joint_states', JointState),
                         ('scan', '/scan', LaserScan)]:
    subs.append(node.create_subscription(cls, topic,
                lambda msg, k=kind: receive(k, msg), qos_profile_sensor_data))
start = time.monotonic()
while time.monotonic() - start < 180:
    rclpy.spin_once(node, timeout_sec=0.1)
    if samples and samples[-1][0] - samples[0][0] >= args.duration:
        break
now = time.monotonic()
tf = {frame: buffer.can_transform('odom', frame, Time())
      for frame in ['base_link', 'lidar_link']}
checks = {
    'complete_observation': bool(samples) and samples[-1][0]-samples[0][0] >= args.duration,
    'all_streams_fresh': all(counts[k] > 0 and now-last_received[k] < 5
                             for k in ['truth', 'odom', 'imu', 'pose', 'joints', 'scan']),
    'standing_height': bool(samples) and all(.20 < s[1] < .30 for s in samples),
    'standing_tilt': bool(samples) and all(math.isfinite(s[2]) and s[2] < 5 for s in samples),
    'scan_returns': scan.get('finite_returns', 0) > 0,
    'tf': all(tf.values()),
}
report = dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
              counts=dict(counts), wall_seconds=round(now-start, 2), tf=tf, scan=scan,
              sim_start=samples[0][0] if samples else None,
              sim_end=samples[-1][0] if samples else None,
              height_min=min(s[1] for s in samples) if samples else None,
              height_max=max(s[1] for s in samples) if samples else None,
              tilt_max_deg=max(s[2] for s in samples) if samples else None,
              xy_displacement=math.hypot(samples[-1][3]-samples[0][3],
                                          samples[-1][4]-samples[0][4]) if samples else None)
Path(args.output).write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
node.destroy_node()
rclpy.shutdown()
raise SystemExit(0 if all(checks.values()) else 1)
