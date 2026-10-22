"""Normalize only the pinned MuJoCo ideal renderer's unset rectification matrix.

The raw message remains on /native/camera_info. K/P/D and capture header are
preserved; this is not a general real-camera calibration or rectification node.
"""
from copy import deepcopy

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo


def normalize_native_info(msg):
    k = np.asarray(msg.k).reshape(3, 3)
    r = np.asarray(msg.r).reshape(3, 3)
    p = np.asarray(msg.p).reshape(3, 4)
    roi = msg.roi
    expected_k = np.array([[k[0, 0], 0, k[0, 2]], [0, k[1, 1], k[1, 2]], [0, 0, 1.]])
    if (msg.header.frame_id != 'camera_optical_frame' or (msg.width, msg.height) != (320, 240)
            or msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec <= 0
            or msg.distortion_model != 'plumb_bob' or len(msg.d) != 5
            or not np.isfinite(msg.d).all() or np.any(np.asarray(msg.d) != 0)
            or not np.isfinite(k).all() or min(k[0, 0], k[1, 1]) <= 0
            or not np.allclose(k, expected_k, atol=1e-12)
            or not np.allclose(p, np.column_stack((k, np.zeros(3))), atol=1e-12)
            or not (np.array_equal(r, np.zeros((3, 3))) or np.array_equal(r, np.eye(3)))
            or msg.binning_x not in (0, 1) or msg.binning_y not in (0, 1)
            or any((roi.x_offset, roi.y_offset, roi.width, roi.height, roi.do_rectify))):
        raise ValueError('input is not the pinned ideal MuJoCo camera contract')
    result = deepcopy(msg)
    result.r = np.eye(3).reshape(-1).tolist()
    return result


class NativeCameraInfoAdapter(Node):
    def __init__(self):
        super().__init__('native_camera_info_adapter')
        self.pub = self.create_publisher(CameraInfo, '/camera/color/camera_info', 5)
        self.sub = self.create_subscription(CameraInfo, '/native/camera_info', self.receive,
                                            qos_profile_sensor_data)

    def receive(self, msg):
        try:
            result = normalize_native_info(msg)
        except ValueError as exc:
            self.get_logger().warning(str(exc))
            return
        self.pub.publish(result)


def main(args=None):
    from .execution import run_node
    run_node(NativeCameraInfoAdapter, args=args)
