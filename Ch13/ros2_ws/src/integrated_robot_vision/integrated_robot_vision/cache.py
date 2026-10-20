"""Bounded, calibrated RGB-D snapshots matched to a detection's capture stamp."""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from threading import RLock
import time

import numpy as np

from .contracts import Intrinsics


def seconds(stamp):
    return stamp.sec + stamp.nanosec / 1e9


def nanoseconds(stamp):
    if not 0 <= stamp.nanosec < 1_000_000_000:
        raise ValueError('normalized ROS stamp required')
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def parse_intrinsics(msg) -> Intrinsics:
    k, r, p = np.array(msg.k).reshape(3, 3), np.array(msg.r).reshape(3, 3), np.array(msg.p).reshape(3, 4)
    roi = msg.roi
    if (msg.distortion_model not in ('', 'plumb_bob', 'rational_polynomial')
            or not np.isfinite(k).all() or not np.isfinite(msg.d).all()
            or np.any(np.array(msg.d) != 0) or not np.allclose(r, np.eye(3), atol=1e-9)
            or not np.allclose(k, [[k[0, 0], 0, k[0, 2]], [0, k[1, 1], k[1, 2]], [0, 0, 1]], atol=1e-9)
            or not (np.array_equal(p, np.zeros((3, 4))) or
                    np.allclose(p, np.column_stack((k, np.zeros(3))), atol=1e-9))
            or msg.binning_x not in (0, 1) or msg.binning_y not in (0, 1)
            or any((roi.x_offset, roi.y_offset, roi.width, roi.height, roi.do_rectify))):
        raise ValueError('rectified, undistorted, unbinned aligned camera required')
    payload = [msg.width, msg.height, msg.header.frame_id, list(msg.k), list(msg.d),
               list(msg.r), list(msg.p), msg.distortion_model, msg.binning_x, msg.binning_y,
               roi.x_offset, roi.y_offset, roi.width, roi.height, roi.do_rectify]
    calibration_id = hashlib.sha256(json.dumps(payload, allow_nan=False).encode()).hexdigest()
    return Intrinsics(msg.width, msg.height, k[0, 0], k[1, 1], k[0, 2], k[1, 2],
                      msg.header.frame_id, calibration_id)


@dataclass(frozen=True)
class FrameBundle:
    rgb: object
    depth: object
    intrinsics: Intrinsics
    stamp: float
    depth_stamp: float
    info_stamp: float
    epoch: int
    receipt_wall: float


class RGBDCache:
    def __init__(self):
        self.lock, self.epoch, self.calibration_id = RLock(), None, None
        self.rgb, self.depth, self.info = OrderedDict(), OrderedDict(), OrderedDict()

    def clear(self, epoch=None):
        with self.lock:
            self.epoch, self.calibration_id = epoch, None
            self.rgb.clear()
            self.depth.clear()
            self.info.clear()

    def _epoch(self, epoch):
        if self.epoch != epoch:
            self.clear(epoch)

    @staticmethod
    def _put(cache, key, value, capacity):
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > capacity:
            cache.popitem(last=False)

    def add_info(self, msg, epoch):
        with self.lock:
            self._epoch(epoch)
            try:
                intrinsics = parse_intrinsics(msg)
                stamp = seconds(msg.header.stamp)
                if nanoseconds(msg.header.stamp) <= 0:
                    raise ValueError('positive calibration capture time required')
            except (ValueError, TypeError):
                self.clear(epoch)
                raise
            if self.calibration_id != intrinsics.calibration_id:
                self.clear(epoch)
                self.calibration_id = intrinsics.calibration_id
            self._put(self.info, stamp, intrinsics, 5)

    def _add_image(self, msg, epoch, cache):
        with self.lock:
            self._epoch(epoch)
            stamp = seconds(msg.header.stamp)
            if nanoseconds(msg.header.stamp) <= 0 or not msg.header.frame_id:
                raise ValueError('positive image capture time and frame required')
            cache.pop(stamp, None)
            if cache is self.rgb and (
                    msg.width <= 0 or msg.height <= 0 or msg.encoding not in ('rgb8', 'bgr8')
                    or msg.step < msg.width*3 or len(msg.data) != msg.step*msg.height):
                raise ValueError('RGB8/BGR8 image with valid dimensions/stride required')
            self._put(cache, stamp, (deepcopy(msg), time.monotonic()), 10)

    def add_rgb(self, msg, epoch):
        self._add_image(msg, epoch, self.rgb)

    def add_depth(self, msg, epoch):
        self._add_image(msg, epoch, self.depth)

    def current(self, bundle):
        with self.lock:
            rgb, depth = self.rgb.get(bundle.stamp), self.depth.get(bundle.depth_stamp)
            return (self.epoch == bundle.epoch and self.calibration_id == bundle.intrinsics.calibration_id
                    and rgb is not None and rgb[0] is bundle.rgb
                    and depth is not None and depth[0] is bundle.depth)

    def match(self, stamp, frame_id: str, epoch: int):
        with self.lock:
            try:
                capture_ns = nanoseconds(stamp) if hasattr(stamp, 'sec') else None
            except ValueError:
                return None
            if capture_ns is not None:
                stamp = seconds(stamp)
            if epoch != self.epoch or not math.isfinite(stamp) or stamp <= 0:
                return None
            rgb_key = next((s for s, (msg, _) in self.rgb.items() if
                            (abs(nanoseconds(msg.header.stamp)-capture_ns) <= 1
                             if capture_ns is not None else abs(s-stamp) <= 1e-9)), None)
            if rgb_key is None or not self.depth or not self.info:
                return None
            rgb, receipt = self.rgb[rgb_key]
            stamp = seconds(rgb.header.stamp)
            source_ns = nanoseconds(rgb.header.stamp)
            depth_key = min(self.depth, key=lambda s: (
                abs(nanoseconds(self.depth[s][0].header.stamp)-source_ns),
                nanoseconds(self.depth[s][0].header.stamp)))
            info_keys = [s for s in self.info if -.03 <= stamp-s <= 1.]
            if abs(nanoseconds(self.depth[depth_key][0].header.stamp)-source_ns) > 30_000_000 or not info_keys:
                return None
            info_key = min(info_keys, key=lambda s: (abs(s-stamp), s))
            k = self.info[info_key]
            depth = self.depth[depth_key][0]
            if (rgb.header.frame_id != frame_id or depth.header.frame_id != frame_id
                    or k.frame_id != frame_id or (rgb.width, rgb.height) != (k.width, k.height)
                    or (depth.width, depth.height) != (k.width, k.height)):
                return None
            return FrameBundle(rgb, depth, k, stamp, depth_key, info_key, epoch, receipt)
