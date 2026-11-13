#!/usr/bin/env python3
"""Ch05 §5.6: measured startup + original wave in REAL Gazebo.

Do not rerun the already accepted simple_controller tests. The 50Hz/20ms
trajectory behavior is measured, not certified as smooth tracking or safe
on actual hardware. Observe a single 3s startup plan in ROS simulation time.
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
from rosgraph_msgs.msg import Clock
from trajectory_msgs.msg import JointTrajectory

OUT=Path(sys.argv[1])
OUT.parent.mkdir(parents=True,exist_ok=True)
JOINTS=("joint1","joint2","joint3","joint4")
rclpy.init()
node=Node("ch05_56_real_wave_feedback_probe")
cmd=[]
meas=[]
last_clock_ns=[None]

def on_clock(msg):
    last_clock_ns[0]=msg.clock.sec*1_000_000_000+msg.clock.nanosec

def on_cmd(msg):
    if list(msg.joint_names)!=list(JOINTS) or len(msg.points)!=1:
        return
    point=msg.points[0]
    if len(point.positions)!=4 or not all(math.isfinite(x) for x in point.positions):
        raise RuntimeError("CH05_56_INVALID_COMMAND")
    cmd.append({
        "t":time.monotonic(),"sim_ns":last_clock_ns[0],
        "positions":[float(x) for x in point.positions],
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
    node.create_subscription(Clock,"/clock",on_clock,25),
]
start=time.monotonic()
try:
    while time.monotonic()-start<12.0:
        rclpy.spin_once(node,timeout_sec=.2)
    if len(cmd)<160:
        raise RuntimeError(f"CH05_56_TOO_FEW_REAL_COMMANDS {len(cmd)}")
    if len(meas)<60:
        raise RuntimeError(f"CH05_56_TOO_FEW_REAL_JOINT_STATES {len(meas)}")
    # A single 3s startup trajectory must precede, and remain distinct
    # from, the original 50Hz wave stream. No 20ms posture jump is permitted.
    ramps=[x for x in cmd if x["horizon_ns"]==3_000_000_000]
    wave=[x for x in cmd if x["horizon_ns"]==20_000_000]
    cmd_horizons=sorted({x["horizon_ns"] for x in cmd})
    if len(ramps)!=1 or cmd[0] is not ramps[0] or len(wave)<160:
        raise RuntimeError(f"CH05_56_START_RAMP_MISSING ramps={len(ramps)} wave={len(wave)}")
    if cmd_horizons!=[20_000_000,3_000_000_000]:
        raise RuntimeError(f"CH05_56_UNEXPECTED_TRAJECTORY_HORIZONS {cmd_horizons}")
    startup_interval_wall_s=wave[0]["t"]-ramps[0]["t"]
    if ramps[0]["sim_ns"] is None or wave[0]["sim_ns"] is None:
        raise RuntimeError("CH05_56_CLOCK_MISSING_FOR_STARTUP_INTERVAL")
    startup_interval_sim_s=(wave[0]["sim_ns"]-ramps[0]["sim_ns"])/1e9
    # The 3s trajectory horizon is ROS /clock, NOT host wall-clock.
    # Under headless Gazebo, the real-time factor is not guaranteed to be 1.
    if not 2.8<=startup_interval_sim_s<=6.5:
        raise RuntimeError(
            f"CH05_56_SIM_STARTUP_INTERVAL_FAIL sim={startup_interval_sim_s:.3f} "
            f"wall={startup_interval_wall_s:.3f}"
        )
    cmd_dts=[b["t"]-a["t"] for a,b in zip(wave,wave[1:])]
    def span(values,index):
        ar=[x["positions"][index] for x in values]
        return max(ar)-min(ar)
    cmd_spans=[span(wave,i) for i in range(4)]
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
    # Inspect physical feedback during the initial ramp, not just
    # message timing or after-the-fact trajectory 'success' log lines.
    ramp_feedback=[m["positions"] for m in meas
                   if ramps[0]["t"]<=m["t"]<=wave[0]["t"]]
    if len(ramp_feedback)<30:
        raise RuntimeError("CH05_56_RAMP_JOINT_FEEDBACK_MISSING")
    r2=[p[1] for p in ramp_feedback]
    r3=[p[2] for p in ramp_feedback]
    if min(r2)<-0.75 or max(r2)>.25 or min(r3)<-.25 or max(r3)>1.05:
        raise RuntimeError(
            f"CH05_56_START_RAMP_OVERSHOOT joint2=[{min(r2)},{max(r2)}] "
            f"joint3=[{min(r3)},{max(r3)}]"
        )
    steady=[m["positions"] for m in meas
            if wave[0]["t"]<=m["t"]<=wave[0]["t"]+1.0]
    if len(steady)<20:
        raise RuntimeError("CH05_56_NO_STEADY_POSE_FEEDBACK")
    errors=[max(abs(p[1]+.5),abs(p[2]-.8)) for p in steady]
    if sorted(errors)[len(errors)//2]>.18:
        raise RuntimeError("CH05_56_START_POSE_NOT_MEASURED_AFTER_RAMP")
    first=cmd[0]["positions"]
    report={
        "chapter":"Ch05","section":"5.6","status":"SCOPED_PASS",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
        "scope":"measured_3s_start_ramp_then_original_50hz_wave_real_gazebo",
        "command_count":len(cmd),"wave_command_count":len(wave),
        "measured_state_count":len(meas),
        "command_median_interval_s":median_dt,
        "observed_command_hz":actual_rate,
        "command_spans_rad":cmd_spans,
        "measured_spans_rad":meas_spans,
        "first_observed_command_rad":first,
        "startup_ramp_goal_duration_sec":3.0,
        "startup_to_wave_sim_time_sec":startup_interval_sim_s,
        "startup_to_wave_wall_time_sec":startup_interval_wall_s,
        "ramp_joint2_observed_min_max_rad":[min(r2),max(r2)],
        "ramp_joint3_observed_min_max_rad":[min(r3),max(r3)],
        "original_trajectory_horizons_ns":cmd_horizons,
        "startup_20ms_posture_jump":"REMOVED_VERIFIED_ONE_3S_GOAL",
        "long_run_tracking_error":"NOT_RUN",
        "safe_start_ramp":"SCOPED_PASS_GAZEBO_SIM_ONLY",
        "actual_hardware":"NOT_RUN","gui":"NOT_RUN",
        "simple_controller_retest":"NOT_RUN","ch10":"HOLD",
    }
    OUT.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("CH05_56_REAL_GAZEBO_WAVE_3S_RAMP_AND_JOINT_MOVEMENT_SCOPED_PASS "
          f"commands={len(cmd)} states={len(meas)} "
          f"command_spans={cmd_spans} measured_spans={meas_spans} "
          f"median_dt={median_dt:.4f}",flush=True)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
