#!/usr/bin/env python3
"""Ch01 §1.6 0.5-second timer exercise on an isolated source copy.

Do not change existing textbook code or rerun accepted 1Hz heartbeat proof.
Probe real rclpy node and interval; send Ctrl+C, audit exit/graph removal.
"""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import rclpy
from rclpy.node import Node

SOURCE=Path(__file__).resolve().parents[1]/"Ch01/robot_ws/src/my_robot_controller/my_robot_controller/simple_controller.py"
OUT=Path(os.environ["CH01_16_OUT"])
OUT.mkdir(parents=True,exist_ok=True)
original=SOURCE.read_text()
needle="self.timer_period = 1.0"
if original.count(needle)!=1:
    raise RuntimeError("CH01_16_BOOK_SOURCE_TIMER_CONTRACT_CHANGED")
staged=Path(tempfile.mkdtemp(prefix="book_ch01_16_"))
script=staged/"simple_controller.py"
script.write_text(original.replace(needle,"self.timer_period = 0.5"))
compile(script.read_text(),str(script),"exec")
print("CH01_16_SOURCE_COPY_ONLY_NO_ORIGINAL_CHANGE_PASS",flush=True)

rclpy.init()
witness=Node("ch01_16_timer_witness")
child=None
log=OUT/"timed_node.log"
try:
    with log.open("w") as f:
        child=subprocess.Popen([sys.executable,"-u",str(script)],
                               stdout=f,stderr=subprocess.STDOUT,
                               start_new_session=True,env=os.environ.copy())
        end=time.monotonic()+9
        received=False
        while time.monotonic()<end:
            rclpy.spin_once(witness,timeout_sec=0.10)
            if any(name=="my_robot_node" for name,ns in witness.get_node_names_and_namespaces()):
                received=True
            text=log.read_text(errors="replace")
            lines=[line for line in text.splitlines() if "Heartbeat:" in line]
            if received and len(lines)>=5:
                break
            if child.poll() is not None:
                raise RuntimeError("CH01_16_NODE_DIED_PREMATURELY")
        else:
            raise RuntimeError("CH01_16_HEARTBEAT_OR_GRAPH_DISCOVERY_TIMEOUT")
        stamps=[];counts=[]
        for line in lines[:5]:
            match=re.search(r"\[INFO\]\s+\[(\d+(?:\.\d+)?)\].*Heartbeat:\s*(\d+)",line)
            if not match:
                raise RuntimeError("CH01_16_HEARTBEAT_TIMESTAMP_UNREADABLE")
            stamps.append(float(match.group(1)))
            counts.append(int(match.group(2)))
        if counts!=list(range(1,6)):
            raise RuntimeError("CH01_16_COUNTER_NOT_SEQUENTIAL")
        intervals=[b-a for a,b in zip(stamps,stamps[1:])]
        if not all(0.30 <= dt <= 0.85 for dt in intervals):
            raise RuntimeError(f"CH01_16_NOT_2HZ actual_intervals={intervals}")
        print("CH01_16_REAL_ROS_2HZ_TIMER_AND_NODE_DISCOVERY_PASS "+str(intervals),
              flush=True)
        os.killpg(child.pid,signal.SIGINT)
        try:
            rc=child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL)
            raise RuntimeError("CH01_16_NODE_DID_NOT_SHUTDOWN_AFTER_CTRL_C")
        if rc!=0:
            raise RuntimeError(f"CH01_16_CTRL_C_EXIT_NONZERO rc={rc}")
        vanished=False
        for _ in range(45):
            rclpy.spin_once(witness,timeout_sec=0.08)
            if not any(name=="my_robot_node" for name,ns in witness.get_node_names_and_namespaces()):
                vanished=True
                break
        if not vanished:
            raise RuntimeError("CH01_16_NODE_REMAINS_AFTER_STOP")
        print("CH01_16_CTRL_C_CLEAN_EXIT_AND_NODE_GRAPH_REMOVAL_PASS",flush=True)
    receipt={
        "chapter":"Ch01","section":"1.6","status":"SCOPED_PASS",
        "scope":"isolated_source_copy_0p5s_actual_rclpy_timer",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
        "original_file_unchanged":SOURCE.read_text()==original,
        "node_name":"my_robot_node",
        "heartbeat_count":len(counts),
        "observed_intervals_s":intervals,
        "requested_timer_period_s":0.5,
        "ctrl_c_exit_code":0,"node_absent_after_shutdown":vanished,
        "gui":"NOT_RUN","original_1hz_retest":"NOT_RUN",
        "manual_oop_explanation":"NOT_RUN","ch10":"HOLD",
    }
    p=OUT/"result.json"
    p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("CH01_16_INDEPENDENT_REAL_TIMER_INTERVAL_RECEIPT_PASS",flush=True)
finally:
    if child is not None and child.poll() is None:
        os.killpg(child.pid,signal.SIGKILL)
        child.wait(timeout=2)
    witness.destroy_node()
    if rclpy.ok():rclpy.shutdown()
    shutil.rmtree(staged,ignore_errors=True)
