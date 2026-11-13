#!/usr/bin/env python3
"""Ch07 §7.5: synchronized optical pixel + measured depth + TF to base_link.

Simulation/education only. Never substitute detector's PointStamped.z
(contour area in px²) for actual depth in metres. No output on invalid data.
"""
import math
import struct
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool
from rclpy.qos import qos_profile_sensor_data
from rclpy.duration import Duration
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


def stamp_s(message):
    h = message.header.stamp
    return h.sec + h.nanosec * 1e-9


def rotate_xyz(x, y, z, q):
    norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
    if not math.isfinite(norm) or norm < 1e-8:
        raise ValueError("invalid quaternion")
    a, b, c, d = q.x/norm, q.y/norm, q.z/norm, q.w/norm
    return (
        (1-2*(b*b+c*c))*x + 2*(a*b-c*d)*y + 2*(a*c+b*d)*z,
        2*(a*b+c*d)*x + (1-2*(a*a+c*c))*y + 2*(b*c-a*d)*z,
        2*(a*c-b*d)*x + 2*(b*c+a*d)*y + (1-2*(a*a+b*b))*z,
    )


def sample_depth_m(msg, u, v):
    if not (0 <= u < msg.width and 0 <= v < msg.height):
        return None
    if msg.encoding not in ("32FC1", "16UC1"):
        return None
    bytes_per_pixel = 4 if msg.encoding == "32FC1" else 2
    offset = int(v)*int(msg.step) + int(u)*bytes_per_pixel
    if offset + bytes_per_pixel > len(msg.data) or msg.step < msg.width*bytes_per_pixel:
        return None
    order = ">" if msg.is_bigendian else "<"
    value = struct.unpack_from(order + ("f" if bytes_per_pixel == 4 else "H"),
                               msg.data, offset)[0]
    z = float(value) if bytes_per_pixel == 4 else float(value)/1000.0
    if not math.isfinite(z) or not (0.15 <= z <= 6.0):
        return None
    return z


class CoordTransformer(Node):
    def __init__(self):
        super().__init__("coord_transformer")
        self.declare_parameter("max_age_sec", 0.8)
        self.declare_parameter("sync_tolerance_sec", 0.08)
        self.valid = False
        self.pixel = None
        self.depth = None
        self.info = None
        self.last_sent_stamp = None
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self, spin_thread=False)
        self.pub = self.create_publisher(PointStamped, "/camera/target_3d_base", 10)
        self.create_subscription(Bool, "/camera/target_valid", self.on_valid, 10)
        self.create_subscription(PointStamped, "/camera/target_pixel", self.on_pixel, 10)
        self.create_subscription(Image, "/camera/depth/image_raw",
                                 self.on_depth, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, "/camera/camera_info",
                                 self.on_info, qos_profile_sensor_data)

    def on_valid(self, msg):
        self.valid = msg.data
        if not self.valid:
            self.pixel = None  # never revive previously detected coordinates
        self.try_project()

    def on_pixel(self, msg):
        self.pixel = msg
        self.try_project()

    def on_depth(self, msg):
        self.depth = msg
        self.try_project()

    def on_info(self, msg):
        self.info = msg
        self.try_project()

    def try_project(self):
        if not self.valid or self.pixel is None or self.depth is None or self.info is None:
            return
        pixel, depth, info = self.pixel, self.depth, self.info
        stamp = stamp_s(pixel)
        if self.last_sent_stamp == stamp:
            return
        now = self.get_clock().now().nanoseconds*1e-9
        max_age = float(self.get_parameter("max_age_sec").value)
        tolerance = float(self.get_parameter("sync_tolerance_sec").value)
        if not math.isfinite(stamp) or not (-0.1 <= now-stamp <= max_age):
            return
        if any(abs(stamp_s(m)-stamp)>tolerance for m in (depth, info)):
            return
        if not (pixel.header.frame_id == depth.header.frame_id ==
                info.header.frame_id == "camera_optical_frame"):
            return
        if info.width != depth.width or info.height != depth.height:
            return
        fx, fy, cx, cy = info.k[0], info.k[4], info.k[2], info.k[5]
        if not all(math.isfinite(v) for v in (fx,fy,cx,cy)) or fx <= 0 or fy <= 0:
            return
        u, v = pixel.point.x, pixel.point.y
        if not math.isfinite(u) or not math.isfinite(v):
            return
        ui, vi = int(round(u)), int(round(v))
        z = sample_depth_m(depth, ui, vi)
        if z is None:
            return
        x = (u-cx)*z/fx
        y = (v-cy)*z/fy
        try:
            transform = self.buffer.lookup_transform(
                "base_link", "camera_optical_frame",
                Time.from_msg(pixel.header.stamp), timeout=Duration(seconds=0.03))
            q = transform.transform.rotation
            translation = transform.transform.translation
            x, y, z = rotate_xyz(x, y, z, q)
        except Exception:
            # TF missing/extrapolation/invalid quaternion: fail closed.
            return
        msg = PointStamped()
        msg.header.frame_id = "base_link"
        msg.header.stamp = pixel.header.stamp
        msg.point.x = float(x + translation.x)
        msg.point.y = float(y + translation.y)
        msg.point.z = float(z + translation.z)
        if not all(math.isfinite(t) for t in
                   (msg.point.x,msg.point.y,msg.point.z)):
            return
        self.pub.publish(msg)
        self.last_sent_stamp = stamp
        self.get_logger().info(
            f"CH07_75_VALID_3D_TARGET stamp={stamp:.6f} "
            f"xyz=({msg.point.x:.6f},{msg.point.y:.6f},{msg.point.z:.6f})")


def main(args=None):
    rclpy.init(args=args)
    node = CoordTransformer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
