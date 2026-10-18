"""Cache contracts reject unregistered or mismatched image geometry."""
from copy import deepcopy
import struct

import numpy as np
import pytest
from sensor_msgs.msg import CameraInfo, Image

from integrated_robot_vision.cache import RGBDCache


def stamp(msg, value):
    ns = round(value * 1e9)
    msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(ns, 1_000_000_000)
    msg.header.frame_id = 'camera_optical_frame'
    return msg


def images(rgb_time=1., depth_time=1.02):
    rgb = stamp(Image(), rgb_time)
    rgb.width = rgb.height = 10
    rgb.encoding, rgb.step, rgb.data = 'rgb8', 30, bytes(300)
    depth = stamp(Image(), depth_time)
    depth.width = depth.height = 10
    depth.encoding, depth.step, depth.data = '32FC1', 40, struct.pack('<100f', *([1.] * 100))
    return rgb, depth


def info(stamp_value=1.):
    msg = stamp(CameraInfo(), stamp_value)
    msg.width = msg.height = 10
    msg.k = [10., 0., 5., 0., 10., 5., 0., 0., 1.]
    msg.r = np.eye(3).reshape(-1).tolist()
    msg.p = [10., 0., 5., 0., 0., 10., 5., 0., 0., 0., 1., 0.]
    msg.d = [0.] * 5
    msg.distortion_model = 'plumb_bob'
    return msg


def populated(depth_time=1.02):
    cache = RGBDCache()
    cache.add_info(info(), 0)
    rgb, depth = images(depth_time=depth_time)
    cache.add_rgb(rgb, 0)
    cache.add_depth(depth, 0)
    return cache


def test_rgbd_cache_matches_exact_capture_and_skew_limit():
    cache = populated()
    bundle = cache.match(1., 'camera_optical_frame', 0)
    assert bundle is not None
    assert bundle.stamp == 1.
    assert bundle.depth_stamp == 1.02
    assert bundle.intrinsics.fx == 10.
    assert cache.match(1.001, 'camera_optical_frame', 0) is None
    assert cache.match(1., 'wrong_frame', 0) is None
    assert populated(1.031).match(1., 'camera_optical_frame', 0) is None


def test_cache_rejects_size_frame_stale_info_and_epoch_mismatch():
    cache = populated()
    assert cache.match(1., 'camera_optical_frame', 1) is None
    wrong = images()[1]
    wrong.width = 9
    cache.add_depth(wrong, 0)
    # Same timestamp replacement must not expose an older matching frame.
    assert cache.match(1., 'camera_optical_frame', 0) is None
    cache = RGBDCache()
    cache.add_info(info(.1), 0)
    rgb, depth = images(1.2, 1.2)
    cache.add_rgb(rgb, 0)
    cache.add_depth(depth, 0)
    assert cache.match(1.2, 'camera_optical_frame', 0) is None


@pytest.mark.parametrize('change', ['distortion', 'model', 'rotation', 'k', 'p', 'roi', 'binning', 'nan'])
def test_unrectified_or_malformed_calibration_invalidates_cache(change):
    cache = populated()
    msg = info()
    if change == 'distortion':
        msg.d[0] = .1
    elif change == 'model':
        msg.distortion_model = 'equidistant'
    elif change == 'rotation':
        msg.r = [0.] * 9
    elif change == 'k':
        msg.k[1] = .1
    elif change == 'p':
        msg.p[3] = .1
    elif change == 'roi':
        msg.roi.width = 5
    elif change == 'binning':
        msg.binning_x = 2
    else:
        msg.k[0] = float('nan')
    with pytest.raises(ValueError):
        cache.add_info(msg, 0)
    assert cache.match(1., 'camera_optical_frame', 0) is None


def test_calibration_change_invalidates_inflight_bundle_and_clears_frames():
    cache = populated()
    bundle = cache.match(1., 'camera_optical_frame', 0)
    assert cache.current(bundle)
    msg = info(1.01)
    msg.k[0] = msg.p[0] = 11.
    cache.add_info(msg, 0)
    assert not cache.current(bundle)
    assert cache.match(1., 'camera_optical_frame', 0) is None
    # Mutation of the caller's message cannot change a cached calibration.
    cache.add_rgb(images()[0], 0)
    cache.add_depth(images()[1], 0)
    msg.k[0] = 999.
    assert cache.match(1., 'camera_optical_frame', 0).intrinsics.fx == 11.


def test_nearest_depth_tie_uses_earlier_and_storage_is_bounded():
    cache = populated(.98)
    cache.add_depth(images(depth_time=1.02)[1], 0)
    assert cache.match(1., 'camera_optical_frame', 0).depth_stamp == .98
    for i in range(30):
        cache.add_rgb(images(2 + i/100, 2 + i/100)[0], 0)
    assert cache.match(1., 'camera_optical_frame', 0) is None


@pytest.mark.parametrize('change', ['encoding', 'step', 'payload'])
def test_malformed_rgb_replacement_cannot_expose_cached_valid_frame(change):
    cache = populated()
    msg = images()[0]
    if change == 'encoding':
        msg.encoding = 'mono8'
    elif change == 'step':
        msg.step = 29
    else:
        msg.data = bytes(299)
    with pytest.raises(ValueError):
        cache.add_rgb(msg, 0)
    assert cache.match(1., 'camera_optical_frame', 0) is None
