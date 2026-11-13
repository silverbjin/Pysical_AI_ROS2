#!/usr/bin/env python3
"""Ch04 §4.3 actual moving TF data, independent of publisher/log strings.

Sections 4.2 static TF and 4.5-4.7 GUI/Gazebo are not rerun.
"""
import json
import math
import os
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage

out=Path(sys.argv[1])
out.parent.mkdir(parents=True,exist_ok=True)

rclpy.init()
node=Node("book_ch04_43_dynamic_tf_evidence")
samples=[]


def on_tf(msg):
    for t in msg.transforms:
        if t.header.frame_id != "world" or t.child_frame_id != "turtle_frame":
            continue
        p=t.transform.translation
        q=t.transform.rotation
        vals=[p.x,p.y,p.z,q.x,q.y,q.z,q.w]
        if not all(map(math.isfinite,vals)):
            continue
        stamp=t.header.stamp.sec*1_000_000_000+t.header.stamp.nanosec
        r=math.hypot(p.x,p.y)
        norm=math.sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w)
        theta=math.atan2(p.y,p.x)
        yaw=2*math.atan2(q.z,q.w)
        tangent_deviation=(yaw-theta-math.pi/2+math.pi)%(2*math.pi)-math.pi
        samples.append({
            "local_monotonic":time.monotonic(),
            "stamp_ns":stamp,"x":p.x,"y":p.y,"z":p.z,
            "radius_m":r,"quaternion_norm":norm,
            "tangent_yaw_error_rad":tangent_deviation,
        })


sub=node.create_subscription(TFMessage,"/tf",on_tf,20)
start=time.monotonic()
try:
    while time.monotonic()-start<5.5:
        rclpy.spin_once(node,timeout_sec=.2)
    good=[s for s in samples if s["stamp_ns"]>0]
    if len(good)<35:
        raise RuntimeError(f"CH04_43_INSUFFICIENT_TF count={len(good)}")
    radii=[s["radius_m"] for s in good]
    qerr=max(abs(s["quaternion_norm"]-1.) for s in good)
    yawerr=max(abs(s["tangent_yaw_error_rad"]) for s in good)
    xs=[s["x"] for s in good];ys=[s["y"] for s in good]
    st={s["stamp_ns"] for s in good}
    if not all(abs(r-2.)<=0.02 for r in radii):
        raise RuntimeError("CH04_43_WRONG_RADIUS")
    if not all(abs(s["z"])<=1e-6 for s in good):
        raise RuntimeError("CH04_43_Z_NOT_ZERO")
    if qerr>0.001 or yawerr>0.015:
        raise RuntimeError(f"CH04_43_WRONG_TANGENT_OR_QUAT qerr={qerr} yaw={yawerr}")
    if max(xs)-min(xs)<.5 or max(ys)-min(ys)<.5 or len(st)<35:
        raise RuntimeError("CH04_43_NOT_DYNAMIC")
    report={
        "chapter":"Ch04","sections":["4.3","4.4"],
        "status":"SCOPED_PASS",
        "source_sha":os.environ.get("RUN_SOURCE_SHA","UNKNOWN"),
        "scope":"real_broadcaster_world_to_turtle_frame_dynamic_tf",
        "actual_tf_samples":len(good),
        "min_radius_m":min(radii),"max_radius_m":max(radii),
        "radius_expected_m":2.0,
        "x_span_m":max(xs)-min(xs),"y_span_m":max(ys)-min(ys),
        "unique_nonzero_stamps":len(st),
        "max_quaternion_norm_error":qerr,
        "max_tangent_yaw_error_rad":yawerr,
        "original_static_tf_retest":"NOT_RUN",
        "gazebo_physics":"NOT_RUN","rviz_gui":"NOT_RUN","hardware":"NOT_RUN",
        "ch10":"HOLD",
    }
    out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("CH04_43_REAL_2M_CIRCULAR_TF_AND_TANGENT_YAW_PASS "+json.dumps({
        "samples":len(good),"radius_min":min(radii),"radius_max":max(radii),
        "x_span":report["x_span_m"],"y_span":report["y_span_m"]}),flush=True)
finally:
    node.destroy_node()
    if rclpy.ok():rclpy.shutdown()
