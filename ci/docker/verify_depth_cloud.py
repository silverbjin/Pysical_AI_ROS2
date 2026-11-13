#!/usr/bin/env python3
"""Ch07 #161: inspect ACTUAL ROS Depth Image and PointCloud2 bytes from Gazebo OGRE2.

Not a repeat of #127 RGB-only CI. Real Depth / Cloud content only; no invented
RGB-depth registration, physical grasp, GUI, or safety acceptance.
"""
import json
import math
from pathlib import Path
import struct
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, PointCloud2, PointField


def timestamp(header):
    return int(header.stamp.sec) * 1_000_000_000 + int(header.stamp.nanosec)


def depth_receipt(msg):
    fmt = {"32FC1": ("f", 4, 1.0), "16UC1": ("H", 2, 0.001)}
    if msg.encoding not in fmt or not msg.width or not msg.height:
        return None
    kind, stride, unit = fmt[msg.encoding]
    if msg.step < msg.width * stride or len(msg.data) < msg.step * msg.height:
        return None
    unpack = struct.Struct((">" if msg.is_bigendian else "<") + kind)
    observed = []
    for y in range(0, msg.height, max(1, msg.height // 16)):
        for x in range(0, msg.width, max(1, msg.width // 20)):
            value = unpack.unpack_from(msg.data, y * msg.step + x * stride)[0] * unit
            if math.isfinite(value) and 0.05 <= value <= 10.0:
                observed.append(value)
    return {
        "stamp_ns": timestamp(msg.header), "frame": msg.header.frame_id,
        "width": msg.width, "height": msg.height, "encoding": msg.encoding,
        "step": msg.step, "bytes": len(msg.data),
        "sampled_valid_positive_m": len(observed),
        "sampled_min_depth_m": min(observed) if observed else None,
        "sampled_max_depth_m": max(observed) if observed else None,
    }


def cloud_receipt(msg):
    if not msg.width or not msg.height or not msg.point_step:
        return None
    fields = {f.name: f for f in msg.fields}
    if any(k not in fields or fields[k].datatype != PointField.FLOAT32 for k in ("x", "y", "z")):
        return None
    if any(fields[k].offset + 4 > msg.point_step for k in ("x", "y", "z")):
        return None
    if msg.row_step < msg.width * msg.point_step or len(msg.data) < msg.row_step * msg.height:
        return None
    fmt = ">" if msg.is_bigendian else "<"
    values = []
    for y in range(0, msg.height, max(1, msg.height // 16)):
        for x in range(0, msg.width, max(1, msg.width // 20)):
            pos = y * msg.row_step + x * msg.point_step
            xyz = [struct.unpack_from(fmt + "f", msg.data, pos + fields[k].offset)[0]
                   for k in ("x", "y", "z")]
            if all(math.isfinite(v) for v in xyz) and xyz[2] > 0:
                values.append(xyz)
    return {
        "stamp_ns": timestamp(msg.header), "frame": msg.header.frame_id,
        "width": msg.width, "height": msg.height, "point_step": msg.point_step,
        "row_step": msg.row_step, "bytes": len(msg.data),
        "xyz_fields": {k: fields[k].offset for k in ("x", "y", "z")},
        "sampled_finite_forward_xyz": len(values),
        "example_xyz_m": values[0] if values else None,
    }


def main():
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node("book_ch07_real_depth_cloud_probe")
    receipts_depth, receipts_cloud = [], []
    qos = QoSProfile(depth=5, history=HistoryPolicy.KEEP_LAST,
                     reliability=ReliabilityPolicy.BEST_EFFORT)

    def on_depth(msg):
        if len(receipts_depth) < 8:
            record = depth_receipt(msg)
            if record is not None:
                receipts_depth.append(record)

    def on_cloud(msg):
        if len(receipts_cloud) < 5:
            record = cloud_receipt(msg)
            if record is not None:
                receipts_cloud.append(record)

    subscriptions = [
        node.create_subscription(Image, "/camera/depth_image", on_depth, qos),
        node.create_subscription(PointCloud2, "/camera/points", on_cloud, qos),
    ]
    try:
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.3)
            if (len({x["stamp_ns"] for x in receipts_depth if x["stamp_ns"] > 0}) >= 2
                    and any(x["sampled_valid_positive_m"] > 0 for x in receipts_depth)
                    and any(x["sampled_finite_forward_xyz"] > 0 for x in receipts_cloud)):
                break
        aligned_frame = all(
            x["frame"] == "camera_optical_frame" and x["stamp_ns"] > 0
            for x in receipts_depth + receipts_cloud
        )
        unique_depth_stamps = len({x["stamp_ns"] for x in receipts_depth if x["stamp_ns"] > 0})
        passed = bool(
            unique_depth_stamps >= 2 and receipts_cloud and aligned_frame
            and any(x["sampled_valid_positive_m"] > 0 for x in receipts_depth)
            and any(x["sampled_finite_forward_xyz"] > 0 for x in receipts_cloud)
        )
        result = {
            "status": "PASS" if passed else "FAIL",
            "scope": "original Gazebo OGRE2 RGB-D actual ROS depth pixels + PointCloud2 XYZ",
            "depth_messages": len(receipts_depth), "point_cloud_messages": len(receipts_cloud),
            "distinct_depth_timestamps": unique_depth_stamps,
            "optical_frame_consistent": aligned_frame,
            "depth_samples": receipts_depth[:4], "cloud_samples": receipts_cloud[:3],
            "not_run": ["exact RGB-depth timestamp correspondence",
                        "pixel-to-point projection alignment and metric accuracy",
                        "GUI/WSLg", "physical grasp", "Ch10"],
        }
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("BOOK_CH07_DEPTH_CLOUD_" + result["status"] + " " +
              json.dumps(result, sort_keys=True), flush=True)
        return 0 if passed else 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
