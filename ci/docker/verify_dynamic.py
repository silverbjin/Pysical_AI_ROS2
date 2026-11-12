#!/usr/bin/env python3
"""Bounded dynamic-only ROS 2 probes. Never upgrade an unrun chapter to PASS.

Usage:
    python3 verify_dynamic.py ch05|ch09|ch11 OUTPUT.json
Ch10 numerical geometry boundary is a separate ROS-free probe.
"""
import json
import math
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Imu, LaserScan
from trajectory_msgs.msg import JointTrajectory
from std_msgs.msg import Float64

mode, filename = sys.argv[1:3]
output = Path(filename)
rclpy.init()
node = Node("book_dynamic_boundary_" + mode)
t0 = time.monotonic()
last = {}
subscribers = []
data = {"mode": mode, "scope": "OBSERVED_DYNAMIC_ONLY", "status": "FAIL",
        "evidence": {}, "unverified": []}


def register(msg_type, topic, fn):
    subscribers.append(node.create_subscription(msg_type, topic, fn, 10))


if mode == "ch05":
    # Reuse original simple_controller running in the same Ch05 live session.
    commands = []
    states = []
    def on_cmd(msg):
        if "joint2" in msg.joint_names and msg.points:
            i = msg.joint_names.index("joint2")
            if i < len(msg.points[0].positions):
                commands.append((time.monotonic(), float(msg.points[0].positions[i])))
    def on_state(msg):
        if "joint2" in msg.name:
            i = msg.name.index("joint2")
            if i < len(msg.position) and math.isfinite(msg.position[i]):
                states.append((time.monotonic(), float(msg.position[i])))
    register(JointTrajectory, "/arm_controller/joint_trajectory", on_cmd)
    register(JointState, "/joint_states", on_state)
    timeout_s = 13
    data["unverified"] = ["three independent cold-starts", "PID tuning", "GUI", "tracking over long trajectories"]
elif mode == "ch09":
    commands = []
    states = []
    joint = "fr_thigh_joint"
    topic = "/model/my_quadruped/joint/fr_thigh_joint/cmd_pos"
    def on_cmd(msg):
        if math.isfinite(msg.data):
            commands.append((time.monotonic(), float(msg.data)))
    def on_state(msg):
        if joint in msg.name:
            i = msg.name.index(joint)
            if i < len(msg.position) and math.isfinite(msg.position[i]):
                states.append((time.monotonic(), float(msg.position[i])))
    register(Float64, topic, on_cmd)
    register(JointState, "/joint_states", on_state)
    timeout_s = 14
    data["unverified"] = ["stand stability", "contact forces", "all twelve controlled joints", "GUI"]
elif mode == "ch11":
    imu = []
    scans = []
    def on_imu(msg):
        z = msg.linear_acceleration.z
        if math.isfinite(z):
            imu.append((time.monotonic(), float(z), msg.header.frame_id,
                        msg.header.stamp.sec, msg.header.stamp.nanosec))
    def on_scan(msg):
        finite = sum(math.isfinite(v) for v in msg.ranges)
        scans.append((time.monotonic(), len(msg.ranges), finite,
                      msg.header.frame_id, msg.header.stamp.sec, msg.header.stamp.nanosec))
    register(Imu, "/imu/data_raw", on_imu)
    register(LaserScan, "/scan", on_scan)
    timeout_s = 22
    data["unverified"] = ["EKF odom TF authority", "slam_toolbox lifecycle",
                          "map save", "sensor quality/loop closure", "GUI"]
else:
    raise SystemExit("Usage: verify_dynamic.py ch05|ch09|ch11 JSON_OUT")

try:
    while time.monotonic() - t0 < timeout_s:
        rclpy.spin_once(node, timeout_sec=0.25)
    if mode == "ch05":
        # Evaluate each unambiguous command at t+1.15s; not just movement after command.
        windows = []
        for tc, goal in commands:
            candidates = [p for ts, p in states if tc + 1.15 <= ts <= tc + 1.70]
            if candidates and (abs(goal - .5) < .01 or abs(goal) < .01):
                windows.append({"target": goal, "measured_last": candidates[-1],
                                "error_rad": abs(goal - candidates[-1])})
        bend = [w for w in windows if abs(w["target"] - .5) < .01]
        home = [w for w in windows if abs(w["target"]) < .01]
        data["evidence"] = {"command_count": len(commands), "state_count": len(states),
                             "settled_windows": windows, "threshold_error_rad": 0.10}
        ok = bool(bend and home and min(w["error_rad"] for w in bend) <= .10
                  and min(w["error_rad"] for w in home) <= .10)
    elif mode == "ch09":
        cmd_span = max([p for _, p in commands]) - min([p for _, p in commands]) if len(commands) > 1 else 0.0
        state_span = max([p for _, p in states]) - min([p for _, p in states]) if len(states) > 1 else 0.0
        data["evidence"] = {"ros_command_samples": len(commands),
                             "ros_measured_joint_samples": len(states),
                             "command_span_rad": cmd_span, "joint_span_rad": state_span,
                             "minimum_joint_span_rad": 0.10}
        ok = len(commands) >= 10 and len(states) >= 10 and cmd_span >= .15 and state_span >= .10
    else:
        data["evidence"] = {
            "imu_samples": len(imu), "scan_samples": len(scans),
            "imu_frame_ids": sorted({x[2] for x in imu}),
            "scan_frame_ids": sorted({x[3] for x in scans}),
            "scan_lengths": sorted({x[1] for x in scans}),
            "scan_valid_counts": [x[2] for x in scans[:6]],
            "imu_stamp_nonzero": any(sec > 0 or ns > 0 for _,_,_,sec,ns in imu),
            "scan_stamp_nonzero": any(sec > 0 or ns > 0 for _,_,_,_,sec,ns in scans),
        }
        ok = len(imu) >= 5 and len(scans) >= 2 and any(n >= 350 and finite > 10 for _,n,finite,*_ in scans)
        ok = ok and data["evidence"]["imu_stamp_nonzero"] and data["evidence"]["scan_stamp_nonzero"]
    data["status"] = "PASS" if ok else "FAIL"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DYNAMIC_" + mode.upper() + "_" + data["status"] + " " +
          json.dumps(data["evidence"], ensure_ascii=False), flush=True)
    sys.exit(0 if ok else 1)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
