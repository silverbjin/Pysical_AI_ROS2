#!/usr/bin/env python3
"""Ch03 §3.9 original keyboard TTY -> actual ROS Float64 command topics.

A real Linux pseudo-terminal drives the published textbook entrypoint.
No Gazebo/robot is launched, so this test MUST NOT claim actuator motion.
"""
import errno
import json
import math
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import termios
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

OUT=Path(os.environ["CH03_39_OUT"])
OUT.mkdir(parents=True,exist_ok=True)
rclpy.init()
witness=Node("ch03_39_independent_ros_topic_witness")
history={1:[],2:[]}


def receive(index):
    def cb(msg):
        if not math.isfinite(msg.data):
            raise RuntimeError("CH03_39_NONFINITE_TOPIC_COMMAND")
        history[index].append((time.monotonic(),float(msg.data)))
    return cb


sub1=witness.create_subscription(Float64,"/joint1/cmd_pos",receive(1),10)
sub2=witness.create_subscription(Float64,"/joint2/cmd_pos",receive(2),10)
master,slave=pty.openpty()
initial_tty=termios.tcgetattr(slave)
child=None
good=False
try:
    env=os.environ.copy()
    env["PYTHONUNBUFFERED"]="1"
    child=subprocess.Popen(
        ["ros2","run","my_robot_description","simple_arm_teleop"],
        stdin=slave,stdout=slave,stderr=slave,
        start_new_session=True,env=env,
    )
    deadline=time.monotonic()+9
    ready=False
    while time.monotonic()<deadline:
        rclpy.spin_once(witness,timeout_sec=.1)
        nodes=[name for name,_ in witness.get_node_names_and_namespaces()]
        pubs1=witness.get_publishers_info_by_topic("/joint1/cmd_pos")
        pubs2=witness.get_publishers_info_by_topic("/joint2/cmd_pos")
        if "simple_arm_teleop" in nodes and pubs1 and pubs2:
            ready=True
            break
        if child.poll() is not None:
            raise RuntimeError("CH03_39_ORIGINAL_TTY_NODE_DIED_DURING_START")
    if not ready:
        raise RuntimeError("CH03_39_ROS_GRAPH_PUBLISHER_DISCOVERY_TIMEOUT")
    # Wait for DDS writer-reader matches before sending the FIRST input.
    # Unlike a bare publisher log, the second process receives each command.
    for _ in range(10):
        rclpy.spin_once(witness,timeout_sec=.08)
    print("CH03_39_ACTUAL_ROS_NODES_AND_TWO_COMMAND_TOPICS_READY",flush=True)

    transitions=[
        ("w",0.05,0.0),
        ("w",0.10,0.0),
        ("a",0.10,0.05),
        ("d",0.10,0.0),
        ("s",0.05,0.0),
    ]
    collected=[]
    for key,j1,j2 in transitions:
        old1=len(history[1]);old2=len(history[2])
        os.write(master,key.encode("ascii"))
        limit=time.monotonic()+4.0
        matched=False
        while time.monotonic()<limit:
            rclpy.spin_once(witness,timeout_sec=.12)
            if len(history[1])>old1 and len(history[2])>old2:
                latest1=history[1][-1][1]
                latest2=history[2][-1][1]
                if abs(latest1-j1)<1e-5 and abs(latest2-j2)<1e-5:
                    matched=True
                    break
            if child.poll() is not None:
                raise RuntimeError("CH03_39_TELEOP_DIED_BEFORE_Q")
        if not matched:
            raise RuntimeError(
                f"CH03_39_KEY_COMMAND_MISMATCH key={key} expected=({j1},{j2}) "
                f"last={[history[1][-1] if history[1] else None,history[2][-1] if history[2] else None]}"
            )
        collected.append({"key":key,"joint1_rad":j1,"joint2_rad":j2})
    print("CH03_39_REAL_PTY_KEYS_AND_ROS_FLOAT64_TWO_JOINTS_PASS",flush=True)

    before1=len(history[1]);before2=len(history[2])
    idle_end=time.monotonic()+0.65
    while time.monotonic()<idle_end:
        rclpy.spin_once(witness,timeout_sec=.12)
    if len(history[1])!=before1 or len(history[2])!=before2:
        raise RuntimeError("CH03_39_IDLE_REPUBLISH_SPAM")
    if any(abs(v)>1.57 for values in history.values() for _,v in values):
        raise RuntimeError("CH03_39_SOFTWARE_CLAMP_VIOLATION")
    print("CH03_39_IDLE_NO_RESEND_AND_JOINT_LIMITS_PASS",flush=True)

    os.write(master,b"q")
    try:
        rc=child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        raise RuntimeError("CH03_39_Q_DID_NOT_EXIT")
    if rc!=0:
        raise RuntimeError(f"CH03_39_Q_NONZERO_EXIT rc={rc}")
    final_tty=termios.tcgetattr(slave)
    if final_tty!=initial_tty:
        raise RuntimeError("CH03_39_TTY_NOT_RESTORED")
    gone=False
    for _ in range(30):
        rclpy.spin_once(witness,timeout_sec=.1)
        if "simple_arm_teleop" not in [
            name for name,_ in witness.get_node_names_and_namespaces()
        ]:
            gone=True;break
    if not gone:
        raise RuntimeError("CH03_39_ROS_NODE_LEFT_AFTER_Q")
    print("CH03_39_Q_EXIT0_TTY_RESTORED_AND_ROS_NODE_GONE_PASS",flush=True)

    good=True
    receipt={
        "chapter":"Ch03","section":"3.9","status":"SCOPED_PASS",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
        "scope":"original_keyboard_node_real_pty_and_ros_joint_topics",
        "tested_input":"w,w,a,d,s,q",
        "observed_transitions":collected,
        "joint1_message_count":len(history[1]),
        "joint2_message_count":len(history[2]),
        "idle_no_republish":True,
        "software_limits_rad":[-1.57,1.57],
        "child_exit_code":rc,
        "tty_attributes_restored":True,
        "ros_node_gone":True,
        "gazebo_joint_feedback":"NOT_RUN",
        "gazebo_world_retest":"NOT_RUN",
        "manual_keyboard_gui":"NOT_RUN",
        "real_robot":"NOT_RUN","ch10":"HOLD",
    }
    (OUT/"result.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("CH03_39_REAL_INTERACTIVE_TTY_AND_ROS_COMMAND_SCOPED_PASS",flush=True)
finally:
    if child is not None and child.poll() is None:
        try: child.terminate();child.wait(timeout=2)
        except subprocess.TimeoutExpired: child.kill();child.wait()
    if child is not None:
        # Flush PTY output for the original process receipt.
        try:
            os.close(slave);slave=-1
            os.set_blocking(master,False)
            data=b""
            for _ in range(40):
                try:chunk=os.read(master,4096)
                except (BlockingIOError,OSError):break
                if not chunk:break
                data+=chunk
            (OUT/"teleop_original_tty.log").write_bytes(data)
        except OSError:pass
    try:os.close(master)
    except OSError:pass
    if slave>=0:
        try:os.close(slave)
        except OSError:pass
    witness.destroy_node()
    if rclpy.ok():rclpy.shutdown()
