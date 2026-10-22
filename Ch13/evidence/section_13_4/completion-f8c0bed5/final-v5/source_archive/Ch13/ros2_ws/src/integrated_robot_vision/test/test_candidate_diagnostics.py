"""An unmatched capture must be explainable before any worker submission."""
import json
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from integrated_robot_vision.contracts import Box2D
from integrated_robot_vision.detectors import to_detection_array
from integrated_robot_vision.vision_processor import VisionProcessor

from test_rgbd_cache import images, info


def test_fusion_requests_reliable_bounded_inputs_for_complete_capture():
    from rclpy.qos import ReliabilityPolicy, HistoryPolicy
    rclpy.init(domain_id=147)
    node = VisionProcessor()
    try:
        # This is our live transport contract, not a source-text/config assertion.
        # Independent best-effort RGB loss made an otherwise complete native
        # depth+detection candidate unusable at capture18.464s in candidate-m10.
        for sub in node.subscriptions_owned:
            qos = sub.qos_profile
            assert qos.reliability == ReliabilityPolicy.RELIABLE, sub.topic_name
            assert qos.history == HistoryPolicy.KEEP_LAST and 0 < qos.depth <= 10
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_unsubmitted_candidate_reports_receipts_and_missing_depth():
    rclpy.init(args=['--ros-args', '-p', 'trace_enabled:=true', '-p',
                    'trace_run_id:=f8c0bed5-cdac-43d8-81ff-84ab88360cdb'], domain_id=147)
    node, peer = VisionProcessor(), Node('candidate_diagnostics_peer')
    executor = SingleThreadedExecutor()
    executor.add_node(peer)
    events = []
    sub = peer.create_subscription(String, '/vision/status',
                                   lambda msg: events.append(json.loads(msg.data)), 50)
    try:
        stamp = peer.get_clock().now().nanoseconds / 1e9
        node.on_info(info(stamp))
        rgb, _ = images(stamp, stamp)
        node.on_rgb(rgb)
        node.on_detections(to_detection_array([Box2D(5., 5., 6., 6., 'fixture_red', 1.)], rgb.header))
        end = time.monotonic() + .15
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.005)
        key = rgb.header.stamp.sec * 1_000_000_000 + rgb.header.stamp.nanosec
        capture = [e for e in events if e.get('capture_ns') == key]
        assert {'RGB_RECEIVED', 'DETECTION_RECEIVED', 'WAIT_DEPTH'} <= {
            e.get('event') for e in capture}, 'unsubmitted candidate has no input/rejection evidence'
        assert all(e['run_id'] == 'f8c0bed5-cdac-43d8-81ff-84ab88360cdb' for e in capture)
        assert not any(e.get('event') == 'SUBMITTED' for e in capture)
    finally:
        executor.shutdown()
        node.destroy_node()
        peer.destroy_node()
        rclpy.try_shutdown()
