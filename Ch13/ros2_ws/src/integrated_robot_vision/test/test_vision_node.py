"""Real ROS input/output boundary for the bounded fusion worker."""
import time

from geometry_msgs.msg import PointStamped, TransformStamped
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

from integrated_robot_vision.vision_processor import VisionProcessor, make_executor
from test_rgbd_cache import images, info, stamp


def test_fusion_trace_uses_capture_stamp_and_actual_receive_order():
    import json
    from std_msgs.msg import String
    rclpy.init(domain_id=145, args=['--ros-args', '-p', 'trace_enabled:=true', '-p',
        'trace_run_id:=424240ff-0bfe-4a4b-92d4-93f6a78d49b8'])
    node, peer, executor = None, None, make_executor()
    try:
        node, peer = VisionProcessor(), Node('fusion_trace_peer')
        executor.add_node(node)
        executor.add_node(peer)
        traces, targets = [], []
        sub = peer.create_subscription(String, '/vision/fusion_trace',
            lambda m: traces.append(json.loads(m.data)), qos_profile_sensor_data)
        target = peer.create_subscription(PointStamped, '/vision/target_raw', targets.append, 10)
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'odom', 'camera_optical_frame'
        transform.transform.rotation.w = 1.
        node.tf_buffer.set_transform_static(transform, 'fusion_trace_test_only')
        capture = peer.get_clock().now().nanoseconds/1e9
        node.on_info(info(capture))
        rgb, depth = images(capture, capture)
        detection = Detection2D()
        detection.bbox.center.position.x = detection.bbox.center.position.y = 5.
        detection.bbox.size_x = detection.bbox.size_y = 6.
        best = ObjectHypothesisWithPose()
        best.hypothesis.class_id, best.hypothesis.score = 'fixture_red', .9
        detection.results = [best]
        message = stamp(Detection2DArray(detections=[detection]), capture)
        # Independent streams may arrive in any order; do not sort their timestamps.
        node.on_detections(message)
        node.on_depth(depth)
        node.on_rgb(rgb)
        deadline = time.monotonic()+.25
        while time.monotonic() < deadline and not (traces and targets):
            executor.spin_once(timeout_sec=.005)
        assert targets, 'original fusion target missing'
        assert traces, 'missing capture-linked fusion trace'
        trace = next(v for v in traces if v['outcome'] == 'PUBLISHED')
        assert trace['capture_ns'] == rgb.header.stamp.sec*1_000_000_000+rgb.header.stamp.nanosec
        assert trace['source_frame'] == 'camera_optical_frame'
        times = trace['times_ns']
        assert times['detection_receive'] <= times['depth_receive'] <= times['rgb_receive']
        for start, end in [('bundle_select', 'work_take'), ('depth_start', 'depth_end'),
                           ('tf_start', 'tf_end'), ('publish_start', 'publish_end')]:
            assert 0 < times[start] <= times[end]
    finally:
        executor.shutdown(timeout_sec=2.)
        if node is not None:
            node.destroy_node()
        if peer is not None:
            peer.destroy_node()
        rclpy.try_shutdown()


def test_ros_fusion_preserves_capture_stamp_and_stops_worker_before_destroy():
    rclpy.init(domain_id=145)
    node, stimulus, executor = None, None, make_executor()
    try:
        node = VisionProcessor()
        stimulus = Node('vision_input_fixture')
        executor.add_node(node)
        executor.add_node(stimulus)
        received, sent = [], set()
        sub = stimulus.create_subscription(PointStamped, '/vision/target_raw', received.append, 10)
        pubs = [stimulus.create_publisher(kind, topic, qos_profile_sensor_data) for kind, topic in [
            (CameraInfo, '/camera/color/camera_info'), (Image, '/camera/color/image_raw'),
            (Image, '/camera/aligned_depth_to_color/image_raw'),
            (Detection2DArray, '/vision/detections')]]
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'odom', 'camera_optical_frame'
        transform.transform.rotation.w = 1.
        node.tf_buffer.set_transform_static(transform, 'known_fixture_extrinsic')
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not received:
            t = stimulus.get_clock().now().nanoseconds / 1e9
            pubs[0].publish(info(t))
            executor.spin_once(timeout_sec=.01)
            rgb, depth = images(t, t)
            pubs[1].publish(rgb)
            pubs[2].publish(depth)
            for _ in range(4):
                executor.spin_once(timeout_sec=.01)
            msg = stamp(Detection2DArray(), t)
            detection = Detection2D()
            detection.bbox.center.position.x = detection.bbox.center.position.y = 5.
            detection.bbox.size_x = detection.bbox.size_y = 6.
            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id, hypothesis.hypothesis.score = 'fixture_red', .9
            detection.results = [hypothesis]
            msg.detections = [detection]
            sent.add((rgb.header.stamp.sec, rgb.header.stamp.nanosec))
            pubs[3].publish(msg)
            executor.spin_once(timeout_sec=.03)
        assert received, 'worker failed to publish a real ROS PointStamped'
        result = received[-1]
        assert (result.point.x, result.point.y, result.point.z) == (0., 0., 1.)
        assert result.header.frame_id == 'odom'
        assert (result.header.stamp.sec, result.header.stamp.nanosec) in sent
    finally:
        executor.shutdown(timeout_sec=2)
        if node is not None:
            node.destroy_node()
            assert not node.worker.is_alive()
        if stimulus is not None:
            stimulus.destroy_node()
        rclpy.try_shutdown()


def test_shutdown_has_no_unretrieved_executor_errors():
    from pathlib import Path
    import subprocess
    import sys
    # A separate process lets Future destructors run before inspecting output.
    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        str(Path(__file__).resolve()) + '::test_ros_fusion_preserves_capture_stamp_and_stops_worker_before_destroy',
        '-q'], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'exception was never retrieved' not in result.stdout + result.stderr
    assert 'Destroyable' not in result.stdout + result.stderr
