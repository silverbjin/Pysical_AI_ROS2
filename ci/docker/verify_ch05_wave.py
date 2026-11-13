#!/usr/bin/env python3
"""Ch05 §5.6: original wave_hello publisher + REAL Gazebo joint feedback.

Do not rerun the already accepted simple_controller tests. The 50Hz/20ms
trajectory behavior is measured, not certified as smooth tracking or safe
on actual hardware. Explicitly report aggressive initial posture jump.
"""
import json
import math
import os
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

OUT=Path(sys.argv[1])
OUT.parent.mkdir(parents=True,exist_ok=True)
JOINTS=("joint1","joint2","joint3","joint4")
rclpy.init()
node=Node("ch05_56_real_wave_feedback_probe")
cmd=[]
meas=[]

def on_cmd(msg):
    if list(msg.joint_names)!=list(JOINTS) or len(msg.points)!=1:
        return
    point=msg.points[0]
    if len(point.positions)!=4 or not all(math.isfinite(x) for x in point.positions):
        raise RuntimeError("CH05_56_INVALID_COMMAND")
    cmd.append({
        "t":time.monotonic(),"positions":[float(x) for x in point.positions],
        "horizon_ns":int(point.time_from_start.sec*1e9+point.time_from_start.nanosec),
    })

def on_joint(msg):
    if any(j not in msg.name for j in JOINTS):
        return
    values=[]
    for j in JOINTS:
        i=msg.name.index(j)
        if i>=len(msg.position) or not math.isfinite(msg.position[i]):
            return
        values.append(float(msg.position[i]))
    meas.append({"t":time.monotonic(),"positions":values})

subs=[
    node.create_subscription(JointTrajectory,"/arm_controller/joint_trajectory",on_cmd,25),
    node.create_subscription(JointState,"/joint_states",on_joint,25),
]
start=time.monotonic()
try:
    while time.monotonic()-start<12.0:
        rclpy.spin_once(node,timeout_sec=.2)
    if len(cmd)<160:
        raise RuntimeError(f"CH05_56_TOO_FEW_REAL_COMMANDS {len(cmd)}")
    if len(meas)<60:
        raise RuntimeError(f"CH05_56_TOO_FEW_REAL_JOINT_STATES {len(meas)}")
    cmd_dts=[b["t"]-a["t"] for a,b in zip(cmd,cmd[1:])]
    cmd_horizons=sorted({x["horizon_ns"] for x in cmd})
    def span(values,index):
        ar=[x["positions"][index] for x in values]
        return max(ar)-min(ar)
    cmd_spans=[span(cmd,i) for i in range(4)]
    meas_spans=[span(meas,i) for i in range(4)]
    n=len(cmd_dts)
    dts=sorted(cmd_dts)
    median_dt=dts[n//2]
    actual_rate=1.0/median_dt if median_dt>0 else 0
    if not (0.008<=median_dt<=.075):
        raise RuntimeError(f"CH05_56_COMMAND_RATE_OUT_OF_BOUNDS dt={median_dt:.5f}")
    if cmd_spans[0]<.45 or cmd_spans[3]<.70:
        raise RuntimeError(f"CH05_56_SINE_WAVE_NOT_PUBLISHED spans={cmd_spans}")
    if meas_spans[0]<.15 or meas_spans[3]<.15:
        raise RuntimeError(f"CH05_56_PHYSICAL_JOINT_FEEDBACK_NO_MOTION spans={meas_spans}")
    if not all(x==20_000_000 for x in cmd_horizons):
        raise RuntimeError(f"CH05_56_ORIGINAL_TRAJECTORY_HORIZON_CHANGED {cmd_horizons}")
    first=cmd[0]["positions"]
    report={
        "chapter":"Ch05","section":"5.6","status":"SCOPED_PASS",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
        "scope":"original_50hz_wave_trajectory_and_real_gazebo_joint_motion",
        "command_count":len(cmd),"measured_state_count":len(meas),
        "command_median_interval_s":median_dt,
        "observed_command_hz":actual_rate,
        "command_spans_rad":cmd_spans,
        "measured_spans_rad":meas_spans,
        "first_observed_command_rad":first,
        "original_trajectory_horizons_ns":cmd_horizons,
        "first_posture_jump_risk":"KNOWN_INITIAL_JOINT2_MINUS_0P5_AND_JOINT3_PLUS_0P8_IN_20MS",
        "long_run_tracking_error":"NOT_RUN",
        "safe_start_ramp":"NOT_RUN",
        "actual_hardware":"NOT_RUN","gui":"NOT_RUN",
        "simple_controller_retest":"NOT_RUN","ch10":"HOLD",
    }
    OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("CH05_56_REAL_GAZEBO_WAVE_COMMAND_AND_JOINT_MOVEMENT_SCOPED_PASS "
          f"commands={len(cmd)} states={len(meas)} "
          f"command_spans={cmd_spans} measured_spans={meas_spans} "
          f"median_dt={median_dt:.4f}",flush=True)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
