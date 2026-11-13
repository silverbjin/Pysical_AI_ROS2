#!/usr/bin/env python3
"""Issue #163: one original OGRE2 sensor, same timestamp/pixel Depth vs PointCloud2.

This is a diagnostic of actual ROS messages, not a synthetic camera fixture,
and not a re-run of accepted RGB or Depth-only tests. Never promote a header
frame-id string alone to geometric correctness.
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
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField


def ns(header):
    return int(header.stamp.sec) * 1000000000 + int(header.stamp.nanosec)


# Target box in the test-only world is approximately central. Choose a small
# grid so each callback reads only 35 corresponding pixels, not entire frames.
U = (260, 280, 300, 320, 340, 360, 380)
V = (210, 225, 240, 255, 270)


def depth_record(msg):
    if (msg.encoding != "32FC1" or msg.width != 640 or msg.height != 480
            or msg.step < 2560 or len(msg.data) < msg.step * msg.height):
        return None
    endian = ">" if msg.is_bigendian else "<"
    pixels = {}
    for v in V:
        for u in U:
            d = struct.unpack_from(endian + "f", msg.data, v * msg.step + u * 4)[0]
            if math.isfinite(d) and 0.05 < d < 10:
                pixels[f"{u},{v}"] = float(d)
    return {"stamp_ns": ns(msg.header), "frame": msg.header.frame_id,
            "encoding": msg.encoding, "width": msg.width, "height": msg.height,
            "valid_grid_pixels": pixels}


def cloud_record(msg):
    if msg.width != 640 or msg.height != 480 or not msg.point_step:
        return None
    fields = {f.name: f for f in msg.fields}
    if (any(k not in fields or fields[k].datatype != PointField.FLOAT32
            for k in ("x", "y", "z")) or
            any(fields[k].offset + 4 > msg.point_step for k in ("x", "y", "z")) or
            msg.row_step < msg.width * msg.point_step or
            len(msg.data) < msg.row_step * msg.height):
        return None
    endian = ">" if msg.is_bigendian else "<"
    pixels = {}
    for v in V:
        for u in U:
            pos = v * msg.row_step + u * msg.point_step
            xyz = [struct.unpack_from(endian + "f", msg.data, pos + fields[k].offset)[0]
                   for k in ("x", "y", "z")]
            if all(math.isfinite(a) for a in xyz):
                pixels[f"{u},{v}"] = [float(a) for a in xyz]
    return {"stamp_ns": ns(msg.header), "frame": msg.header.frame_id,
            "width": msg.width, "height": msg.height,
            "point_step": msg.point_step, "row_step": msg.row_step,
            "xyz_field_offsets": {k: fields[k].offset for k in ("x", "y", "z")},
            "finite_grid_points": pixels}


def info_record(msg):
    if msg.width != 640 or msg.height != 480:
        return None
    fx, fy, cx, cy = msg.k[0], msg.k[4], msg.k[2], msg.k[5]
    if not all(math.isfinite(a) for a in (fx, fy, cx, cy)) or fx <= 0 or fy <= 0:
        return None
    return {"stamp_ns": ns(msg.header), "frame": msg.header.frame_id,
            "fx": fx, "fy": fy, "cx": cx, "cy": cy}


def audit(depth, cloud, intrinsics):
    records = []
    matched_stamps = sorted(set(depth) & set(cloud) & set(intrinsics))
    for stamp in matched_stamps:
        d, c, k = depth[stamp], cloud[stamp], intrinsics[stamp]
        if not (d["frame"] == c["frame"] == k["frame"] == "camera_optical_frame"):
            continue
        for key, value in d["valid_grid_pixels"].items():
            xyz = c["finite_grid_points"].get(key)
            if xyz is None:
                continue
            u, v = map(int, key.split(","))
            expected = [(u - k["cx"]) * value / k["fx"],
                        (v - k["cy"]) * value / k["fy"], value]
            # Gazebo native camera convention (+X forward, +Y left, +Z up)
            # converted to ROS optical (+Z forward, +X right, +Y down):
            # optical = (-y_native, -z_native, x_native)
            converted = [-xyz[1], -xyz[2], xyz[0]]
            e_direct = math.dist(xyz, expected)
            e_native = math.dist(converted, expected)
            records.append({"stamp_ns": stamp, "u": u, "v": v,
                            "depth_m": value, "cloud_xyz_reported": xyz,
                            "optical_xyz_expected_from_K": expected,
                            "direct_optical_error_m": e_direct,
                            "native_to_optical_error_m": e_native})
    return records


def main():
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node("book_ch07_163_matched_depth_cloud_diagnostic")
    depth, cloud, intrinsics, rgb = {}, {}, {}, {}
    qos = QoSProfile(depth=10, history=HistoryPolicy.KEEP_LAST,
                     reliability=ReliabilityPolicy.BEST_EFFORT)

    def hold(mapping, message, fn):
        record = fn(message)
        if record and record["stamp_ns"] > 0:
            mapping[record["stamp_ns"]] = record
            # Stores only small grid samples, not whole sensor buffers.
            if len(mapping) > 150:
                mapping.pop(next(iter(mapping)))

    subs = [
        node.create_subscription(Image, "/camera/depth_image",
                                 lambda m: hold(depth, m, depth_record), qos),
        node.create_subscription(PointCloud2, "/camera/points",
                                 lambda m: hold(cloud, m, cloud_record), qos),
        node.create_subscription(CameraInfo, "/camera/camera_info",
                                 lambda m: hold(intrinsics, m, info_record), qos),
        node.create_subscription(Image, "/camera/image_raw",
                                 lambda m: rgb.update({ns(m.header):
                                     {"stamp_ns": ns(m.header),
                                      "frame": m.header.frame_id, "encoding": m.encoding}})
                                 if ns(m.header) > 0 else None, qos),
    ]
    try:
        start = time.monotonic()
        while time.monotonic() - start < 31:
            rclpy.spin_once(node, timeout_sec=0.25)
            records = audit(depth, cloud, intrinsics)
            if len(records) >= 7 and len({r["stamp_ns"] for r in records}) >= 2:
                break
        records = audit(depth, cloud, intrinsics)
        direct = sorted(r["direct_optical_error_m"] for r in records)
        native = sorted(r["native_to_optical_error_m"] for r in records)
        valid = len(records) >= 3
        # Classify, never claim correction from just an axis guess.
        if not valid:
            verdict = "INSUFFICIENT_MATCHED_REAL_SENSOR_DATA"
        elif direct[len(direct)//2] < 0.08:
            verdict = "OPTICAL_DIRECT_NUMERIC_CONSISTENT"
        elif native[len(native)//2] < 0.08 and direct[len(direct)//2] > 0.25:
            verdict = "NATIVE_CAMERA_X_FORWARD_UNDER_OPTICAL_HEADER"
        else:
            verdict = "UNRESOLVED_GEOMETRY_MISMATCH"
        aligned = verdict == "OPTICAL_DIRECT_NUMERIC_CONSISTENT"
        record = {
            "issue": 163, "status": "PASS" if aligned else "FAIL",
            "verdict": verdict, "checked_same_stamp_and_pixel": valid,
            "source": "actual Gazebo OGRE2 RGB-D ROS depth/cloud streams",
            "depth_frames": len(depth), "cloud_frames": len(cloud),
            "camera_info_frames": len(intrinsics), "rgb_frames": len(rgb),
            "shared_depth_cloud_info_stamps": len(set(depth)&set(cloud)&set(intrinsics)),
            "shared_rgb_depth_stamps": len(set(rgb)&set(depth)),
            "sample_count": len(records),
            "median_direct_optical_error_m": direct[len(direct)//2] if direct else None,
            "median_native_to_optical_error_m": native[len(native)//2] if native else None,
            "samples": records[:15],
            "not_run": ["physical RGB/depth photometric registration",
                        "full-calibration geometric accuracy", "physical grasp",
                        "GUI/WSLg", "hardware", "Ch10"],
        }
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        print("CH07_163_MATCHED_PIXEL_" + verdict + " " +
              json.dumps({k: v for k, v in record.items() if k != "samples"}), flush=True)
        return 0 if aligned else 42
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
