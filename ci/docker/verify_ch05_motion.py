#!/usr/bin/env python3
"""Require measured Ch05 joint-state movement, not publisher logs alone."""
import json
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

output = Path(sys.argv[1])
rclpy.init()
node = Node("ch05_real_feedback_probe")
samples = []
targets = []

def on_state(msg):
    if "joint2" not in msg.name:
        return
    index = msg.name.index("joint2")
    if index < len(msg.position) and math.isfinite(msg.position[index]):
        samples.append(float(msg.position[index]))

def on_command(msg):
    if "joint2" not in msg.joint_names or not msg.points:
        return
    index = msg.joint_names.index("joint2")
    if index < len(msg.points[0].positions):
        targets.append(float(msg.points[0].positions[index]))

node.create_subscription(JointState, "/joint_states", on_state, 10)
node.create_subscription(JointTrajectory, "/arm_controller/joint_trajectory", on_command, 10)
start = time.monotonic()
ok = False
try:
    while time.monotonic() - start < 24:
        rclpy.spin_once(node, timeout_sec=.4)
        if len(samples) > 4 and any(abs(g-.5) < .02 for g in targets) and max(samples)-min(samples) >= .15:
            ok = True
            break
    report = {
        "status": "PASS" if ok else "FAIL",
        "scope": "Ch05 joint2 actual JointState relative movement",
        "goal_0_5rad_observed": any(abs(g-.5) < .02 for g in targets),
        "command_samples": len(targets),
        "measured_samples": len(samples),
        "measured_min": min(samples) if samples else None,
        "measured_max": max(samples) if samples else None,
        "required_delta_rad": .15
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    if not ok:
        print("CH05_MEASURED_MOTION_FAIL " + json.dumps(report), file=sys.stderr)
        sys.exit(1)
    print("CH05_MEASURED_MOTION_PASS " + json.dumps(report), flush=True)
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
