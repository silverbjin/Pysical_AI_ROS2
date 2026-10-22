"""Replay capture-time TF/depth through real ROS target output and watchdog."""
import math
import time

import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import PointStamped, TransformStamped
from integrated_robot_interfaces.msg import TrackedTarget
from rclpy.node import Node

from integrated_robot_vision.cache import RGBDCache
from integrated_robot_vision.contracts import Box2D
from integrated_robot_vision.vision_processor import VisionProcessor, capture_observations, make_executor
from test_rgbd_cache import images, info


def bundle_at(stamp):
    cache = RGBDCache()
    cache.add_info(info(stamp), 0)
    rgb, depth = images(stamp, stamp)
    cache.add_rgb(rgb, 0)
    cache.add_depth(depth, 0)
    return cache.match(rgb.header.stamp, 'camera_optical_frame', 0)


@pytest.mark.parametrize('event', ['timeout', 'calibration'])
def test_stamped_track_filter_and_steady_watchdog_preserve_last_capture_time(event):
    rclpy.init(domain_id=147)
    node, observer, executor = None, None, make_executor()
    try:
        node, observer = VisionProcessor(), Node('target_message_observer')
        executor.add_node(node)
        executor.add_node(observer)
        tracks, filtered = [], []
        subs = [observer.create_subscription(TrackedTarget, '/vision/tracked_target', tracks.append, 10),
                observer.create_subscription(PointStamped, '/vision/target_filtered', filtered.append, 10)]
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and not observer.count_publishers('/vision/tracked_target'):
            executor.spin_once(timeout_sec=.01)
        assert observer.count_publishers('/vision/tracked_target') == 1
        for _ in range(10):
            executor.spin_once(timeout_sec=.005)
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'odom', 'camera_optical_frame'
        transform.transform.rotation.w = 1.
        node.tf_buffer.set_transform_static(transform, 'replay_capture_pose')
        node.observe_clock()
        now = node.get_clock().now().nanoseconds/1e9
        node.on_info(info(now))
        first, second = bundle_at(now-.15), bundle_at(now-.05)
        for bundle, pixel in [(first, 5.), (second, 6.)]:
            samples = capture_observations(bundle, [Box2D(pixel, 5, 6, 6, 'cup', .9)],
                                            node.tf_buffer, still_valid=lambda: True)
            with node.lock:
                node.publish_observations(samples, bundle)
        deadline = time.monotonic() + .2
        while time.monotonic() < deadline and len([v for v in tracks if v.valid]) < 2:
            executor.spin_once(timeout_sec=.01)
        valid = [v for v in tracks if v.valid]
        assert len(valid) == 2
        assert valid[0].track_id == valid[1].track_id
        assert valid[-1].header.frame_id == 'odom'
        assert valid[-1].source_header == second.rgb.header
        assert valid[-1].header.stamp == second.rgb.header.stamp
        assert valid[-1].position.x == pytest.approx(.1*(1-math.exp(-.5)), abs=1e-6)
        assert valid[-1].score == pytest.approx(.9)
        assert np.isfinite(valid[-1].covariance).all()
        assert np.linalg.eigvalsh(np.array(valid[-1].covariance).reshape(3, 3)).min() >= 0
        if event == 'calibration':
            changed = info(node.get_clock().now().nanoseconds/1e9)
            changed.k[0] = changed.p[0] = 20.
            node.on_info(changed)
            deadline = time.monotonic() + .1
            while time.monotonic() < deadline and not any(not v.valid for v in tracks):
                executor.spin_once(timeout_sec=.005)
            assert any(not v.valid and v.status == 'RESET' for v in tracks)
        deadline = time.monotonic() + .45
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.01)
        invalid = [v for v in tracks if not v.valid]
        assert invalid and invalid[-1].status == ('LOST' if event == 'timeout' else 'RESET')
        assert invalid[-1].header.stamp == second.rgb.header.stamp
        assert invalid[-1].source_header == second.rgb.header
        assert len(filtered) == 2
    finally:
        executor.shutdown(timeout_sec=2)
        if node is not None:
            node.destroy_node()
        if observer is not None:
            observer.destroy_node()
        rclpy.try_shutdown()


def test_small_clock_rollback_clears_dynamic_tf_but_keeps_static_extrinsics():
    from rclpy.parameter import Parameter
    from rclpy.time import Time
    rclpy.init(domain_id=148)
    node = None
    try:
        node = VisionProcessor()
        assert node.set_parameters([Parameter('use_sim_time', value=True)])[0].successful
        node.get_clock().set_ros_time_override(Time(seconds=2.))
        node.observe_clock()
        dynamic = TransformStamped()
        dynamic.header.frame_id, dynamic.child_frame_id = 'odom', 'old_epoch_frame'
        dynamic.header.stamp = Time(seconds=1.95).to_msg()
        dynamic.transform.rotation.w = 1.
        static = TransformStamped()
        static.header.frame_id, static.child_frame_id = 'odom', 'fixed_sensor_mount'
        static.transform.rotation.w = 1.
        node.tf_buffer.set_transform(dynamic, 'old_epoch')
        node.tf_buffer.set_transform_static(static, 'physical_extrinsic')
        assert node.tf_buffer.can_transform('odom', 'old_epoch_frame', Time(seconds=1.95))
        node.get_clock().set_ros_time_override(Time(seconds=1.9))
        node.observe_clock()
        assert not node.tf_buffer.can_transform('odom', 'old_epoch_frame', Time(seconds=1.95))
        assert node.tf_buffer.can_transform('odom', 'fixed_sensor_mount', Time(seconds=1.9))
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
