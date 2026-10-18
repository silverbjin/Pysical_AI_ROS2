"""Cross-topic DDS arrival order is not capture order: use real messages and tf2."""
import time

from geometry_msgs.msg import TransformStamped
from integrated_robot_interfaces.msg import TrackedTarget
from integrated_robot_vision.contracts import Box2D
from integrated_robot_vision.detectors import to_detection_array
from integrated_robot_vision.vision_processor import VisionProcessor
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from test_rgbd_cache import images, info


def test_detection_arriving_before_aligned_images_waits_without_invalidating_live_track():
    rclpy.init(domain_id=147)
    node, peer, executor = None, None, SingleThreadedExecutor()
    try:
        node, peer = VisionProcessor(), Node('reordered_sensor_test')
        executor.add_node(node)
        executor.add_node(peer)
        states = []
        sub = peer.create_subscription(TrackedTarget, '/vision/tracked_target', states.append, 10)
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'odom', 'camera_optical_frame'
        transform.transform.rotation.w = 1.
        node.tf_buffer.set_transform_static(transform, 'unit_test_camera_not_native_evidence')

        def pump_until(predicate, timeout=.2):
            deadline = time.monotonic()+timeout
            while not predicate() and time.monotonic() < deadline:
                executor.spin_once(timeout_sec=.005)
            assert predicate()

        capture = peer.get_clock().now().nanoseconds/1e9
        node.on_info(info(capture))
        rgb, depth = images(capture, capture)
        node.on_rgb(rgb)
        node.on_depth(depth)
        node.on_detections(to_detection_array([Box2D(5., 5., 6., 6., 'fixture_red', 1.)], rgb.header))
        pump_until(lambda: bool(states) and states[-1].valid)
        previous_count = len(states)
        capture = peer.get_clock().now().nanoseconds/1e9
        rgb, depth = images(capture, capture)
        node.on_detections(to_detection_array([Box2D(5., 5., 6., 6., 'fixture_red', 1.)], rgb.header))
        end = time.monotonic()+.03
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.005)
        assert all(v.valid for v in states[previous_count:]), 'arrival reordering must not publish INVALID'
        node.on_rgb(rgb)
        node.on_depth(depth)
        pump_until(lambda: any(v.valid and v.source_header.stamp == rgb.header.stamp
                               for v in states[previous_count:]))
        count = len(states)
        old, _ = images(capture-.1, capture-.1)
        node.on_detections(to_detection_array([Box2D(5., 5., 6., 6., 'fixture_red', 1.)], old.header))
        end = time.monotonic()+.02
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.005)
        assert all(v.valid for v in states[count:]), 'older inference must not replace/invalidate newer state'
        # A detection with no corresponding images still cannot renew the old track.
        capture = peer.get_clock().now().nanoseconds/1e9
        absent, _ = images(capture, capture)
        node.on_detections(to_detection_array([Box2D(5., 5., 6., 6., 'fixture_red', 1.)], absent.header))
        pump_until(lambda: not states[-1].valid, timeout=.45)
        # The older track expires before this newer pending capture's own TTL.
        pump_until(lambda: node.pending_detection is None, timeout=.15)
    finally:
        executor.shutdown(timeout_sec=2.)
        if node is not None:
            node.destroy_node()
        if peer is not None:
            peer.destroy_node()
        rclpy.try_shutdown()
