#!/usr/bin/env python3
"""Observe actual EKF /odom, TF and scan gate, optional live SLAM map.

This is a simulator pipeline probe: Gazebo ground truth is the odometry input.
It never claims encoder/contact odometry, navigational accuracy, or loop closure.
"""
import json
import math
import sys
import time
from pathlib import Path
from collections import Counter
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan
from tf2_msgs.msg import TFMessage

out=Path(sys.argv[1])
out.parent.mkdir(parents=True,exist_ok=True)
rclpy.init()
node=Node("book_ch11_ekf_scan_probe")
odom, raw, scans, transforms, maps=[],[],[],[],[]
def record_odom(m,dest):
    q=m.pose.pose.orientation
    p=m.pose.pose.position
    if all(math.isfinite(v) for v in (q.x,q.y,q.z,q.w,p.x,p.y,p.z)):
        dest.append({"stamp":m.header.stamp.sec*1_000_000_000+m.header.stamp.nanosec,
                     "frame":m.header.frame_id,"child":m.child_frame_id,
                     "x":p.x,"y":p.y,"z":p.z,
                     "cov0":m.pose.covariance[0]})
sensor=QoSProfile(history=HistoryPolicy.KEEP_LAST,depth=10,
                  reliability=ReliabilityPolicy.BEST_EFFORT)
latched=QoSProfile(history=HistoryPolicy.KEEP_LAST,depth=10,
                  reliability=ReliabilityPolicy.RELIABLE,
                  durability=DurabilityPolicy.TRANSIENT_LOCAL)
subscriptions=[
node.create_subscription(Odometry,"/odom",lambda m:record_odom(m,odom),10),
node.create_subscription(Odometry,"/odom/raw",lambda m:record_odom(m,raw),10),
node.create_subscription(LaserScan,"/scan/slam",lambda m:scans.append((m.header.stamp.sec,len(m.ranges))),sensor),
node.create_subscription(TFMessage,"/tf",lambda m:transforms.extend(
    [(t.header.frame_id,t.child_frame_id) for t in m.transforms]),10),
node.create_subscription(OccupancyGrid,"/map",lambda m:maps.append((m.info.width,m.info.height)),latched)
]
start=time.monotonic()
try:
    while time.monotonic()-start<33:
        rclpy.spin_once(node,timeout_sec=.35)
        if len(odom)>=10 and len(raw)>=10 and len(scans)>=3 and \
           ("odom","base_footprint") in transforms and maps:
            break
    evidence={
        "ekf_filtered_odom_samples":len(odom),
        "gazebo_ground_truth_adapter_samples":len(raw),
        "scan_gate_samples":len(scans),
        "filtered_odom_frames":sorted({(m["frame"],m["child"]) for m in odom}),
        "tf_pairs":sorted(set(transforms))[:30],
        "maps_observed":len(maps),
        "last_map_dimensions":maps[-1] if maps else None,
        "sensor_stamp_nonzero":any(t>0 for t,_ in scans),
        "filtered_odom_stamp_nonzero":any(m["stamp"]>0 for m in odom),
        "first_filtered_covariance_x":odom[0]["cov0"] if odom else None,
        "not_run":["accurate localization versus physical ground truth",
                   "loop closure", "relocalization", "map save on disk",
                   "RViz/WSL2 visual acceptance"]
    }
    required=len(odom)>=10 and len(raw)>=10 and len(scans)>=3 and \
        ("odom","base_footprint") in transforms and evidence["sensor_stamp_nonzero"] and \
        evidence["filtered_odom_stamp_nonzero"]
    # Map might legitimately need motion; retain as NOT_RUN if missing rather than promote map.
    status="PASS" if required else "FAIL"
    result={"status":status,"scope":"EKF filtered odom + TF and TF-gated scan",
            "map_status":"OBSERVED" if maps else "NOT_RUN_OR_NO_MAP",
            "whole_chapter_accepted":False,"evidence":evidence}
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("BOOK_CH11_LOCALIZATION_"+status+" "+json.dumps(evidence),flush=True)
    sys.exit(0 if status=="PASS" else 1)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
