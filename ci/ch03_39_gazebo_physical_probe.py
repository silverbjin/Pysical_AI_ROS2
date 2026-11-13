#!/usr/bin/env python3
"""Ch03 3.9 ONLY missing boundary: real PTY -> book teleop -> Gazebo joints.

Requires prestarted real Gazebo robot, bridge, and real JointState feedback.
Do NOT claim original stand/base stability, exact PID tracking or GUI.
"""
import json
import math
import os
from pathlib import Path
import pty
import subprocess
import sys
import termios
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock

ROOT=Path(os.environ["CH03_39_PHYS_OUT"])
ROOT.mkdir(parents=True,exist_ok=True)
rclpy.init()
node=Node("ch03_39_independent_physical_teleop_witness")
commands={1:[],2:[]}
states=[]
clock=[]

def on_command(i):
    def callback(msg):
        if math.isfinite(msg.data):
            commands[i].append([time.monotonic(),float(msg.data)])
    return callback

def on_states(msg):
    lookup={}
    for i,name in enumerate(msg.name):
        if i>=len(msg.position):
            continue
        for j in ("joint1","joint2"):
            if name==j or name.endswith("::"+j):
                lookup[j]=float(msg.position[i])
    if len(lookup)==2 and all(math.isfinite(x) for x in lookup.values()):
        states.append([time.monotonic(),lookup["joint1"],lookup["joint2"]])

def on_clock(msg):
    clock.append(msg.clock.sec*1_000_000_000+msg.clock.nanosec)

subs=[
 node.create_subscription(Float64,"/joint1/cmd_pos",on_command(1),20),
 node.create_subscription(Float64,"/joint2/cmd_pos",on_command(2),20),
 node.create_subscription(JointState,"/joint_states",on_states,30),
 node.create_subscription(Clock,"/clock",on_clock,20),
]
master,slave=pty.openpty()
original_attrs=termios.tcgetattr(slave)
child=None

def spin_for(duration):
    end=time.monotonic()+duration
    while time.monotonic()<end:
        rclpy.spin_once(node,timeout_sec=.08)

def await_witness():
    end=time.monotonic()+8.0
    while time.monotonic()<end:
        rclpy.spin_once(node,timeout_sec=.1)
        names={x for x,_ in node.get_node_names_and_namespaces()}
        if "simple_arm_teleop" in names and len(states)>=15 and len(set(clock))>=8:
            return
        if child.poll() is not None:
            raise RuntimeError("CH03_39_PHYS_ORIGINAL_TELEOP_DIED_EARLY")
    raise RuntimeError("CH03_39_PHYS_ORIGINAL_NODE_OR_GAZEBO_JOINT_STATE_MISSING")

def send_keys(keys, spacing=0.16):
    for key in keys:
        os.write(master,key.encode("ascii"))
        spin_for(spacing)

def current_stats():
    if not states:
        raise RuntimeError("CH03_39_PHYS_NO_REAL_JOINT_STATES")
    return {
       "joint1_min":min(s[1] for s in states),
       "joint1_max":max(s[1] for s in states),
       "joint2_min":min(s[2] for s in states),
       "joint2_max":max(s[2] for s in states),
    }

try:
    child=subprocess.Popen(
        ["ros2","run","my_robot_description","simple_arm_teleop"],
        stdin=slave,stdout=slave,stderr=slave,start_new_session=True,
        env={**os.environ,"PYTHONUNBUFFERED":"1"},
    )
    await_witness()
    start_obs=current_stats()
    print("CH03_39_REAL_GAZEBO_BOTH_JOINTS_INITIAL_STATE_READY",flush=True)
    # Previous PTY-only CI already proved individual key mappings. Only
    # drive two physical joints here with 0.3rad gradual goal increments.
    send_keys("wwwwww")
    spin_for(1.1)
    first=current_stats()
    send_keys("aaaaaa")
    spin_for(1.3)
    second=current_stats()
    if not commands[1] or not commands[2]:
        raise RuntimeError("CH03_39_PHYS_NO_ROS_COMMAND_MESSAGES")
    c1=[v for _,v in commands[1]]
    c2=[v for _,v in commands[2]]
    if max(c1)<0.29 or max(c2)<0.29:
        raise RuntimeError(
            f"CH03_39_PHYS_COMMAND_TARGETS_MISSING j1_max={max(c1)} j2_max={max(c2)}")
    if first["joint1_max"]-start_obs["joint1_min"]<.12:
        raise RuntimeError(f"CH03_39_PHYS_GAZEBO_JOINT1_NO_MOVEMENT {first}")
    if second["joint2_max"]-start_obs["joint2_min"]<.12:
        raise RuntimeError(f"CH03_39_PHYS_GAZEBO_JOINT2_NO_MOVEMENT {second}")
    print(
       "CH03_39_REAL_PTY_TO_GAZEBO_TWO_ACTUAL_JOINTS_MOVED_PASS "
       f"joint1_span={second['joint1_max']-second['joint1_min']:.5f} "
       f"joint2_span={second['joint2_max']-second['joint2_min']:.5f}",
       flush=True)

    os.write(master,b"q")
    try:
        rc=child.wait(timeout=6)
    except subprocess.TimeoutExpired:
        raise RuntimeError("CH03_39_PHYS_Q_EXIT_TIMEOUT")
    if rc!=0:
        raise RuntimeError(f"CH03_39_PHYS_Q_EXIT_NONZERO {rc}")
    if termios.tcgetattr(slave)!=original_attrs:
        raise RuntimeError("CH03_39_PHYS_TTY_NOT_RESTORED")
    spin_for(.5)
    names={x for x,_ in node.get_node_names_and_namespaces()}
    if "simple_arm_teleop" in names:
        raise RuntimeError("CH03_39_PHYS_NODE_LEFT_BEHIND")
    print("CH03_39_REAL_PTY_Q_NORMAL_EXIT_AND_TTY_RESTORE_PASS",flush=True)
    output={
      "chapter":"Ch03","section":"3.9","status":"SCOPED_PASS",
      "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
      "scope":"actual_ros_teleop_PTY_to_two_Gazebo_physical_joint_states",
      "input_keys":"wwwwwwaaaaaaq",
      "command_joint1_max_rad":max(c1),
      "command_joint2_max_rad":max(c2),
      "command_joint1_count":len(c1),
      "command_joint2_count":len(c2),
      "gazebo_joint_state_messages":len(states),
      "joint_state_stats":second,
      "clock_messages":len(clock),
      "pty_restored":True,"process_exit_code":rc,"original_node_removed":True,
      "original_tty_only_retest":"NOT_RUN",
      "original_world_only_retest":"NOT_RUN",
      "exact_tracking":"NOT_RUN","gui":"NOT_RUN",
      "actual_hardware":"NOT_RUN","ch10":"HOLD",
    }
    (ROOT/"receipt.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print("CH03_39_ACTUAL_INTERACTIVE_GAZEBO_FEEDBACK_SCOPED_PASS",flush=True)
finally:
    if child is not None and child.poll() is None:
        child.terminate()
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:child.kill();child.wait()
    try:
        os.close(slave)
        os.set_blocking(master,False)
        data=b""
        for _ in range(60):
            try:
                chunk=os.read(master,4096)
            except (BlockingIOError,OSError):
                break
            if not chunk:break
            data+=chunk
        (ROOT/"teleop_tty.log").write_bytes(data)
    except OSError:pass
    try:os.close(master)
    except OSError:pass
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
