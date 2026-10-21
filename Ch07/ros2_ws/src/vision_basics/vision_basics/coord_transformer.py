#!/usr/bin/env python3
"""7.5: depth+pixel -> stamped metric point in base_link; fail closed."""
import math

import numpy as np
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import PointStamped
from message_filters import ApproximateTimeSynchronizer, Subscriber
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from tf2_geometry_msgs import do_transform_point
from tf2_ros import Buffer, TransformException, TransformListener

from vision_basics.projection_math import back_project


class CoordTransformer(Node):
    def __init__(self):
        super().__init__('coord_transformer')
        self.declare_parameter('max_age_sec', 0.5)
        self.declare_parameter('min_depth_m', 0.1)
        self.declare_parameter('max_depth_m', 5.0)
        self.max_age = float(self.get_parameter('max_age_sec').value)
        self.min_depth = float(self.get_parameter('min_depth_m').value)
        self.max_depth = float(self.get_parameter('max_depth_m').value)
        if self.max_age <= 0 or self.min_depth <= 0 or self.max_depth <= self.min_depth:
            raise ValueError('invalid max_age_sec/depth range')
        self.info = None
        self.bridge = CvBridge()
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.info_sub = self.create_subscription(
            CameraInfo, '/camera/camera_info', self.set_info, qos_profile_sensor_data)
        self.pixel_sub = Subscriber(self, PointStamped, '/camera/target_pixel',
                                    qos_profile=qos_profile_sensor_data)
        self.depth_sub = Subscriber(self, Image, '/camera/depth/image_raw',
                                    qos_profile=qos_profile_sensor_data)
        self.sync = ApproximateTimeSynchronizer(
            [self.pixel_sub, self.depth_sub], queue_size=10, slop=0.08)
        self.sync.registerCallback(self.convert)
        self.pub = self.create_publisher(PointStamped, '/robot/target_position', 10)

    def set_info(self, msg):
        if msg.width > 0 and msg.height > 0 and msg.k[0] > 0 and msg.k[4] > 0:
            self.info = msg

    def convert(self, pixel, depth):
        info = self.info
        if info is None or not pixel.header.frame_id or not depth.header.frame_id:
            return
        if (pixel.header.frame_id != depth.header.frame_id
                or info.header.frame_id != depth.header.frame_id):
            self.get_logger().warning('RGB/depth/CameraInfo frames differ: alignment required')
            return
        try:
            stamp = Time.from_msg(pixel.header.stamp)
            age = (self.get_clock().now() - stamp).nanoseconds * 1e-9
            if stamp.nanoseconds == 0 or age < -0.1 or age > self.max_age:
                return
            u, v = float(pixel.point.x), float(pixel.point.y)
            if not math.isfinite(u) or not math.isfinite(v):
                return
            x_idx, y_idx = int(round(u)), int(round(v))
            if (x_idx < 0 or y_idx < 0 or
                    x_idx >= depth.width or y_idx >= depth.height or
                    depth.width != info.width or depth.height != info.height):
                return
            raw = self.bridge.imgmsg_to_cv2(depth, desired_encoding='passthrough')
            if depth.encoding == '16UC1':
                z_m = float(raw[y_idx, x_idx]) / 1000.0
            elif depth.encoding == '32FC1':
                z_m = float(raw[y_idx, x_idx])
            else:
                self.get_logger().warning('Unsupported depth encoding: ' + depth.encoding)
                return
            x, y, z = back_project(u, v, z_m, float(info.k[0]),
                                   float(info.k[4]), float(info.k[2]),
                                   float(info.k[5]), self.min_depth, self.max_depth)
            camera_point = PointStamped()
            camera_point.header = pixel.header
            camera_point.point.x, camera_point.point.y, camera_point.point.z = x, y, z
            tf = self.tf_buffer.lookup_transform(
                'base_link', camera_point.header.frame_id, stamp,
                timeout=Duration(seconds=0.1))
            self.pub.publish(do_transform_point(camera_point, tf))
        except (ValueError, TypeError, IndexError, CvBridgeError, TransformException) as exc:
            self.get_logger().warning(f'Ignoring invalid 3D target: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = CoordTransformer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
