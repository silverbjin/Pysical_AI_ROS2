#!/usr/bin/env python3
"""Ch04 §4.7: true original Ch03 joint2 CLI -> Gazebo position feedback.

NOT fake JointState publishers. Check the original ROS->GZ bridge + Gazebo
JointPositionController output and RSP TF; no physical hardware claim.
"""
import json
import math
import os
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage

OUT=Path(sys.argv[1])
OUT.parent.mkdir(parents=True,exist_ok=True)
rclpy.init()
node=Node("book_ch04_47_actual_joint2_witness")
cmd=[]
states=[]
tf2_stamps=[]
clocks=[]

def on_cmd(msg):
    if math.isfinite(msg.data):
        cmd.append((time.monotonic(),float(msg.data)))

def on_state(msg):
    indices=[i for i,n in enumerate(msg.name)
             if n=="joint2" or n.endswith("::joint2")]
    if len(indices)!=1:
        return
    i=indices[0]
    if i>=len(msg.position) or not math.isfinite(msg.position[i]):
        return
    states.append((time.monotonic(),float(msg.position[i]),
                   msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec))

def on_tf(msg):
    for t in msg.transforms:
        if t.child_frame_id=="link2" and t.header.frame_id=="link1":
            tf2_stamps.append(t.header.stamp.sec*1_000_000_000+
                              t.header.stamp.nanosec)

def on_clock(msg):
    clocks.append(msg.clock.sec*1_000_000_000+msg.clock.nanosec)

subs=[
    node.create_subscription(Float64,"/joint2/cmd_pos",on_cmd,20),
    node.create_subscription(JointState,"/joint_states",on_state,30),
    node.create_subscription(TFMessage,"/tf",on_tf,30),
    node.create_subscription(Clock,"/clock",on_clock,30),
]
try:
    start=time.monotonic()
    while time.monotonic()-start<12.5:
        rclpy.spin_once(node,timeout_sec=.2)
    if len(cmd)<4 or len(states)<50 or len(clocks)<30:
        raise RuntimeError(
            f"CH04_47_INSUFFICIENT_REAL_MESSAGES commands={len(cmd)} "
            f"states={len(states)} clocks={len(clocks)}"
        )
    values=[v for _,v in cmd]
    if not any(abs(v+0.785)<.02 for v in values):
        raise RuntimeError("CH04_47_MINUS_GOAL_NOT_PUBLISHED")
    if not any(abs(v-0.785)<.02 for v in values):
        raise RuntimeError("CH04_47_PLUS_GOAL_NOT_PUBLISHED")
    if not all(abs(abs(v)-0.785)<.02 for v in values):
        raise RuntimeError("CH04_47_UNEXPECTED_CONTROL_SOURCE")
    observed=[v for _,v,_ in states]
    span=max(observed)-min(observed)
    if span<.40:
        raise RuntimeError(f"CH04_47_REAL_GAZEBO_JOINT2_NO_MOTION span={span}")
    if not (min(observed)<-.10 and max(observed)>.10):
        raise RuntimeError(
            f"CH04_47_REAL_GAZEBO_JOINT2_DID_NOT_REVERSE "
            f"min={min(observed)} max={max(observed)}"
        )
    if not any(t>0 for _,_,t in states):
        raise RuntimeError("CH04_47_GAZEBO_JOINT_STAMPS_ZERO")
    if len(tf2_stamps)<5 or not any(t>0 for t in tf2_stamps):
        raise RuntimeError("CH04_47_RSP_DYNAMIC_TF_ABSENT")
    if len(set(clocks))<15 or max(clocks)<=min(clocks):
        raise RuntimeError("CH04_47_SIM_CLOCK_NOT_ADVANCING")

    # Compare each alternating command with the actual next measured window.
    windows=[]
    for ts,goal in cmd:
        observed_later=[pos for when,pos,_ in states
                        if ts+.5 <= when <= ts+2.2]
        if observed_later:
            windows.append({
                "goal_rad":goal,
                "measured_min_rad":min(observed_later),
                "measured_max_rad":max(observed_later),
                "nearest_goal_error_rad":min(abs(goal-x) for x in observed_later)
            })
    if len(windows)<3:
        raise RuntimeError("CH04_47_NO_JOINT_FEEDBACK_WINDOWS")
    receipt={
        "chapter":"Ch04","section":"4.7","status":"SCOPED_PASS",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
        "scope":"original_ch03_joint2_cli_gz_joint_position_controller_ros_bridge_real_joint_states_tf",
        "command_count":len(cmd),
        "measured_joint_state_count":len(states),
        "actual_measured_joint2_min_rad":min(observed),
        "actual_measured_joint2_max_rad":max(observed),
        "actual_measured_joint2_span_rad":span,
        "observed_command_goals_rad":values,
        "command_to_actual_windows":windows,
        "actual_tf_dynamic_count":len(tf2_stamps),
        "clock_count":len(clocks),
        "original_ch04_joint_position_cli":"NOT_IMPLEMENTED",
        "ros_controller_type":"Gazebo JointPositionController, not ros2_control",
        "exact_tracking_and_overshoot":"NOT_ACCEPTED_FROM_THIS_PROBE",
        "rviz_gui":"NOT_RUN",
        "actual_robot":"NOT_RUN","ch10":"HOLD",
    }
    OUT.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(f"CH04_47_REAL_GAZEBO_JOINT2_COMMAND_TO_MEASURED_REVERSAL_PASS "
          f"commands={len(cmd)} states={len(states)} tf={len(tf2_stamps)} "
          f"min={min(observed):.5f} max={max(observed):.5f} span={span:.5f}",flush=True)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
