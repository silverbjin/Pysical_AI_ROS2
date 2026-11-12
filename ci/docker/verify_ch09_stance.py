#!/usr/bin/env python3
"""Observe actual Gazebo base posture after the book's original stand_up node.

Criterion is posture stability (roll/pitch/height/drift), not foot-ground contact
forces, controller robustness, or real-robot acceptance.
"""
import json
import math
from pathlib import Path
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState

out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
rclpy.init()
node=Node("ch09_stance_physics_observer")
odom=[]
states=[]
def angles(q):
    # Roll, pitch from normalized odometry quaternion.
    v=(q.x,q.y,q.z,q.w)
    m=math.sqrt(sum(x*x for x in v))
    if m < 0.01 or not math.isfinite(m):return (float("nan"),float("nan"))
    x,y,z,w=(a/m for a in v)
    roll=math.atan2(2*(w*x+y*z),1-2*(x*x+y*y))
    sinp=max(-1.,min(1.,2*(w*y-z*x)))
    return math.asin(sinp),roll  # pitch, roll

def on_odom(m):
    pose=m.pose.pose
    pitch,roll=angles(pose.orientation)
    xyz=(pose.position.x,pose.position.y,pose.position.z)
    if all(math.isfinite(v) for v in xyz+(pitch,roll)):
        odom.append((time.monotonic(),xyz,pitch,roll,
                     m.header.stamp.sec*1000000000+m.header.stamp.nanosec))
def on_joint(m):
    targets={"fr_thigh_joint","fl_thigh_joint","rr_thigh_joint","rl_thigh_joint",
             "fr_calf_joint","fl_calf_joint","rr_calf_joint","rl_calf_joint"}
    observed={n:p for n,p in zip(m.name,m.position) if n in targets and math.isfinite(p)}
    if len(observed)>=8:states.append((time.monotonic(),observed))
sub0=node.create_subscription(Odometry,"/stand_observation/odom",on_odom,qos_profile_sensor_data)
sub1=node.create_subscription(JointState,"/joint_states",on_joint,10)
start=time.monotonic()
try:
    while time.monotonic()-start<17:
        rclpy.spin_once(node,timeout_sec=.3)
    # Late-window stability does not reward a robot that briefly stands then collapses.
    tmax=max((s[0] for s in odom),default=0.)
    tail=[s for s in odom if s[0]>=tmax-4.0]
    tail_heights=[s[1][2] for s in tail]
    tail_rolls=[abs(s[3]) for s in tail]
    tail_pitches=[abs(s[2]) for s in tail]
    travel=math.hypot(tail[-1][1][0]-tail[0][1][0],
                      tail[-1][1][1]-tail[0][1][1]) if len(tail)>=2 else float("inf")
    max_tilt_deg=math.degrees(max(tail_rolls+tail_pitches)) if tail else None
    height_spread=max(tail_heights)-min(tail_heights) if tail else None
    min_height=min(tail_heights) if tail else None
    stamp_count=len({s[4] for s in odom if s[4]>0})
    ok=(len(odom)>=50 and len(states)>=30 and len(tail)>=15 and
        stamp_count>=40 and min_height is not None and min_height>=.12 and
        max_tilt_deg is not None and max_tilt_deg<=20.0 and
        height_spread is not None and height_spread<=.08 and travel<=.20)
    evidence={
        "model_odometry_samples":len(odom),
        "joint_state_samples_with_eight_leg_joints":len(states),
        "distinct_nonzero_sim_stamps":stamp_count,
        "late_window_seconds":4.0,
        "late_window_samples":len(tail),
        "min_base_height_m":min_height,
        "late_window_height_spread_m":height_spread,
        "late_window_max_abs_roll_or_pitch_deg":max_tilt_deg,
        "late_window_horizontal_displacement_m":travel,
        "requirements":{"min_base_z_m":.12,"max_tilt_deg":20.,
                        "max_height_drift_m":.08,"max_horizontal_drift_m":.20},
        "instrumentation":"OdometryPublisher added ONLY to generated URDF in CI; untouched source",
        "not_run":["measured foot-ground contact forces","three independent stances",
                   "joint limit and steady-state torque","real-hardware stability","GUI"]}
    result={"chapter":"Ch09","scope":"posture-only stability after original stand_up",
            "status":"PASS" if ok else "FAIL","whole_chapter_accepted":False,
            "evidence":evidence}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("CH09_POSTURE_STABILITY_"+result["status"]+" "+json.dumps(evidence),flush=True)
    sys.exit(0 if ok else 1)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
