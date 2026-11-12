#!/usr/bin/env python3
"""Headless, simulation-only ROS probes beyond existing accepted smoke checks.

ch09: original stand_up sends all 12 joint commands; verify ROS transport and
measured movement of at least four joints. NOT a balance/contact or gait test.

ch11: source is Gazebo /simulation/odom (OdometryPublisher plugin). Verify
the existing sim_odometry adapter emits physical /odom/raw observations with
matching timestamp and pose. NOT an EKF/SLAM/map test.
"""
import json
import math
from pathlib import Path
import sys
import time
from collections import defaultdict

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from nav_msgs.msg import Odometry

mode = sys.argv[1]
output = Path(sys.argv[2])
rclpy.init()
node = Node("book_extended_" + mode)
start = time.monotonic()
report = {"mode": mode, "status": "FAIL", "scope": "SIM_ONLY"}
subscriptions = []

if mode == "ch09":
    prefixes = ("fr", "fl", "rr", "rl")
    kinds = ("hip", "thigh", "calf")
    names = [f"{leg}_{kind}_joint" for leg in prefixes for kind in kinds]
    targets = {name: (0.0 if name.endswith("hip_joint") else
                       -0.6 if name.endswith("thigh_joint") else 1.2)
               for name in names}
    seen_cmd = defaultdict(list)
    seen_states = defaultdict(list)

    def state_cb(msg):
        for name, position in zip(msg.name, msg.position):
            if name in targets and math.isfinite(position):
                seen_states[name].append((time.monotonic(), float(position)))

    subscriptions.append(node.create_subscription(JointState, "/joint_states", state_cb, 10))

    def make_cb(joint):
        return lambda msg: (seen_cmd[joint].append((time.monotonic(), float(msg.data)))
                            if math.isfinite(msg.data) else None)

    for name in names:
        topic = f"/model/my_quadruped/joint/{name}/cmd_pos"
        subscriptions.append(node.create_subscription(Float64, topic, make_cb(name), 10))
    timeout = 16.0
elif mode == "ch11":
    measured = []
    adapted = []

    def obs(msg, destination):
        pos = msg.pose.pose.position
        quat = msg.pose.pose.orientation
        stamp = msg.header.stamp
        values = [pos.x, pos.y, pos.z, quat.x, quat.y, quat.z, quat.w]
        if not all(math.isfinite(v) for v in values):
            return
        destination.append({
            "stamp": stamp.sec * 1_000_000_000 + stamp.nanosec,
            "frame": msg.header.frame_id,
            "child": msg.child_frame_id,
            "xyz": [pos.x, pos.y, pos.z],
        })

    subscriptions.append(node.create_subscription(
        Odometry, "/simulation/odom", lambda m: obs(m, measured), qos_profile_sensor_data))
    subscriptions.append(node.create_subscription(
        Odometry, "/odom/raw", lambda m: obs(m, adapted), 10))
    timeout = 16.0
else:
    raise SystemExit("Usage: verify_extended.py ch09|ch11 OUTPUT_JSON")

try:
    while time.monotonic() - start < timeout:
        rclpy.spin_once(node, timeout_sec=.25)
    if mode == "ch09":
        missing_cmd = sorted(set(names) - set(seen_cmd))
        missing_states = sorted(set(names) - set(seen_states))
        cmd_errors = {n: min(abs(v - targets[n]) for _, v in vals)
                      for n, vals in seen_cmd.items() if vals}
        movement = {n: (max(v for _, v in vals) - min(v for _, v in vals))
                    for n, vals in seen_states.items() if vals}
        responsive = sorted(n for n, span in movement.items() if span >= 0.08)
        report.update({
            "expected_joints": names,
            "missing_command_topics": missing_cmd,
            "missing_measured_joints": missing_states,
            "command_min_errors_rad": cmd_errors,
            "joint_position_spans_rad": movement,
            "responsive_joints_at_least_0_08rad": responsive,
            "unverified": ["body equilibrium", "feet-ground contact", "joint tracking precision",
                           "all 12 joints responsive", "three independent cold starts"],
        })
        ok = not missing_cmd and not missing_states and len(responsive) >= 4
        ok = ok and all(cmd_errors[n] <= .015 for n in names)
        ok = ok and all(len(seen_states[n]) >= 10 for n in names)
    else:
        measurements_by_stamp = {x["stamp"]: x for x in measured}
        pairs = [(measurements_by_stamp[o["stamp"]], o) for o in adapted
                 if o["stamp"] in measurements_by_stamp]
        matching = []
        for left, right in pairs:
            if (left["frame"] == right["frame"] == "odom" and
                left["child"] == right["child"] == "base_footprint" and
                max(abs(a-b) for a,b in zip(left["xyz"],right["xyz"])) <= 0.001):
                matching.append(right)
        stamps = [x["stamp"] for x in adapted]
        report.update({
            "source_observations": len(measured),
            "adapted_observations": len(adapted),
            "matched_sample_stamps_and_positions": len(matching),
            "adapted_stamp_monotonic": all(x < y for x,y in zip(stamps, stamps[1:])),
            "observed_frame_ids": sorted(set((x["frame"], x["child"]) for x in adapted)),
            "unverified": ["EKF fused odometry", "odom->base_footprint TF from EKF",
                           "slam_toolbox active", "map saved", "localization accuracy"],
        })
        ok = len(measured) >= 10 and len(adapted) >= 10 and len(matching) >= 5
        ok = ok and report["adapted_stamp_monotonic"]
    report["status"] = "PASS" if ok else "FAIL"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("BOOK_EXTENDED_" + mode.upper() + "_" + report["status"] + " " +
          json.dumps(report, ensure_ascii=False), flush=True)
    sys.exit(0 if ok else 1)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
