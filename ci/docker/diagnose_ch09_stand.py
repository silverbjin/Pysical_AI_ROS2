#!/usr/bin/env python3
"""One Ch09 diagnostic after known 40.7deg stance FAIL. NOT an acceptance PASS.

Uses only original ROS stand_up command topics, real Gazebo model odometry,
and 12 real JointState values. Does not alter physics, target, gains or URDF.
"""
import json
import math
from collections import defaultdict
from pathlib import Path
import statistics
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
legs=("fr","fl","rr","rl")
kinds=("hip","thigh","calf")
names=[f"{l}_{k}_joint" for l in legs for k in kinds]
targets={n:{"hip":0.0,"thigh":-.6,"calf":1.2}[n.split("_")[1]]
         for n in names}
counts=defaultdict(int)
lastcmd={}
poses=[]
states=[]
rclpy.init()
node=Node("book_ch09_failure_boundary")
start=time.monotonic()

def rot_euler(q):
    x,y,z,w=q
    norm=math.sqrt(sum(v*v for v in q))
    if norm<.01:raise ValueError("quaternion invalid")
    x,y,z,w=(v/norm for v in q)
    roll=math.atan2(2*(w*x+y*z),1-2*(x*x+y*y))
    pitch=math.asin(max(-1,min(1,2*(w*y-z*x))))
    yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
    return [math.degrees(v) for v in (roll,pitch,yaw)]

def on_odom(m):
    p=m.pose.pose.position
    q=m.pose.pose.orientation
    values=[p.x,p.y,p.z,q.x,q.y,q.z,q.w]
    if not all(math.isfinite(v) for v in values):return
    pose={"t":round(time.monotonic()-start,3),"xyz":values[:3],
          "quat_xyzw":values[3:],"rpy_deg":rot_euler(values[3:]),
          "frame":m.header.frame_id,"child":m.child_frame_id,
          "sim_stamp_ns":m.header.stamp.sec*1000000000+m.header.stamp.nanosec}
    poses.append(pose)

def on_joint(m):
    vals=dict(zip(m.name,m.position))
    if not all(n in vals and math.isfinite(vals[n]) for n in names):return
    t=time.monotonic()-start
    if not states or t-states[-1]["t"]>.18:
        states.append({"t":round(t,3),"q":{n:float(vals[n]) for n in names}})

def make_cb(n):
    def cb(msg):
        if math.isfinite(msg.data):
            counts[n]+=1
            lastcmd[n]=float(msg.data)
    return cb

subs=[node.create_subscription(Odometry,"/stand_observation/odom",on_odom,
                               qos_profile_sensor_data),
      node.create_subscription(JointState,"/joint_states",on_joint,10)]
for name in names:
    topic=f"/model/my_quadruped/joint/{name}/cmd_pos"
    subs.append(node.create_subscription(Float64,topic,make_cb(name),10))

try:
    while time.monotonic()-start<18:
        rclpy.spin_once(node,timeout_sec=.25)
    end=max([p["t"] for p in poses],default=0)
    latep=[p for p in poses if p["t"]>=end-4]
    lates=[s for s in states if s["t"]>=end-4]
    median={n:round(statistics.median([s["q"][n] for s in lates]),6)
            if lates else None for n in names}
    errors={n:round(abs(median[n]-targets[n]),6) if median[n] is not None
            else None for n in names}
    pair={}
    for k in kinds:
        pair[k]={
            "left_right_front":None if median[f"fr_{k}_joint"] is None else
                 round(median[f"fr_{k}_joint"]-median[f"fl_{k}_joint"],6),
            "left_right_rear":None if median[f"rr_{k}_joint"] is None else
                 round(median[f"rr_{k}_joint"]-median[f"rl_{k}_joint"],6),
            "front_rear_right":None if median[f"fr_{k}_joint"] is None else
                 round(median[f"fr_{k}_joint"]-median[f"rr_{k}_joint"],6),
            "front_rear_left":None if median[f"fl_{k}_joint"] is None else
                 round(median[f"fl_{k}_joint"]-median[f"rl_{k}_joint"],6)}
    roll=[abs(p["rpy_deg"][0]) for p in latep]
    pitch=[abs(p["rpy_deg"][1]) for p in latep]
    complete=(len(poses)>=50 and len(lates)>=12 and
              all(counts[n]>=10 for n in names))
    flags={
      "joint_target_error_gt_0_2_rad":[n for n in names if
           errors[n] is not None and errors[n]>.2],
      "joint_symmetry_diff_gt_0_15_rad":[f"{k}/{side}" for k,groups in pair.items()
           for side,v in groups.items() if v is not None and abs(v)>.15],
      "roll_gt_20_deg":bool(roll and max(roll)>20),
      "pitch_gt_20_deg":bool(pitch and max(pitch)>20)}
    result={
      "status":"DIAG_CAPTURED" if complete else "DIAG_INCOMPLETE",
      "chapter_accepted":False,
      "previous_stance_status":"FAIL_40_70877_DEG",
      "source":"actual original 12 joint commands and Gazebo odometry",
      "nominal_joint_targets":targets,
      "commands":{"count":dict(counts),"last_value":lastcmd},
      "observed":{
        "odom_samples":len(poses),"sampled_joint_states":len(states),
        "odom_frames":sorted(set(p["frame"]+"->"+p["child"] for p in poses)),
        "sim_stamp_count":len(set(p["sim_stamp_ns"] for p in poses if p["sim_stamp_ns"]>0)),
        "late_median_joint_positions":median,
        "late_joint_target_abs_errors":errors,
        "symmetry_signed_differences":pair,
        "late_max_abs_roll_deg":max(roll) if roll else None,
        "late_max_abs_pitch_deg":max(pitch) if pitch else None,
        "late_median_roll_deg":statistics.median([p["rpy_deg"][0] for p in latep]) if latep else None,
        "late_median_pitch_deg":statistics.median([p["rpy_deg"][1] for p in latep]) if latep else None,
        "initial_odom":poses[0] if poses else None,
        "last_odom":poses[-1] if poses else None,
        "last_joint_state":states[-1] if states else None,
        "early_attitude_samples":poses[:80:10],
        "late_attitude_samples":latep[::max(1,len(latep)//12)],
      },
      "hypothesis_flags":flags,
      "not_run":["real foot-ground contact forces","contact points or impulses",
                 "support polygon", "hardware", "GUI", "controller tuning"],
      "note":"DIAG_CAPTURED only means enough measurements for failure analysis; NOT stance PASS"}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("CH09_ROOT_CAUSE_"+result["status"]+" "+
          json.dumps({"last_rpy":result["observed"]["last_odom"]["rpy_deg"] if poses else None,
              "errors":errors,"symmetry":pair,"flags":flags},ensure_ascii=False),flush=True)
    sys.exit(0 if complete else 2)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
