"""Real ROS delayed inference must retain capture time and reject expired jobs."""
import time
import json

import numpy as np
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray
from std_srvs.srv import SetBool
from threading import Event

from integrated_robot_vision.object_detector import ObjectDetector
from test_rgbd_cache import info, stamp


def test_detector_bounds_opencv_pool_before_inference():
    import cv2
    previous = cv2.getNumThreads()
    cv2.setNumThreads(8)
    rclpy.init(domain_id=146)
    detector = None
    try:
        detector = ObjectDetector(parameter_overrides=[Parameter('backend', value='color_fixture')])
        image = np.zeros((240,320,3), np.uint8)
        image[100:130,150:180,2] = 255
        assert len(detector.backend.detect(image)) == 1
        assert cv2.getNumThreads() == 1, 'detector consumed an unbudgeted OpenCV worker pool'
    finally:
        if detector is not None:
            detector.destroy_node()
        rclpy.try_shutdown()
        cv2.setNumThreads(previous)


def test_detector_requests_reliable_bounded_rgb_and_calibration():
    from rclpy.qos import ReliabilityPolicy, HistoryPolicy
    rclpy.init(domain_id=146)
    detector = ObjectDetector(parameter_overrides=[Parameter('backend', value='color_fixture')])
    try:
        for sub in (detector.rgb_sub, detector.info_sub):
            assert sub.qos_profile.reliability == ReliabilityPolicy.RELIABLE
            assert sub.qos_profile.history == HistoryPolicy.KEEP_LAST
            assert 0 < sub.qos_profile.depth <= 10
    finally:
        detector.destroy_node()
        rclpy.shutdown()


def test_rejected_future_image_has_capture_linked_ingress_evidence():
    rclpy.init(domain_id=146)
    detector = ObjectDetector(parameter_overrides=[
        Parameter('backend', value='color_fixture'), Parameter('trace_enabled', value=True),
        Parameter('trace_run_id', value='f8c0bed5-cdac-43d8-81ff-84ab88360cdb')])
    peer = Node('detector_rejection_peer')
    executor = SingleThreadedExecutor()
    executor.add_node(peer)
    events = []
    sub = peer.create_subscription(String, '/vision/detector_status',
                                   lambda msg: events.append(json.loads(msg.data)), 50)
    try:
        now = detector.get_clock().now().nanoseconds / 1e9
        calibration = info(now)
        calibration.width, calibration.height = 100, 80
        detector.on_info(calibration)
        rgb = stamp(Image(), now + .2)
        rgb.width, rgb.height, rgb.step, rgb.encoding = 100, 80, 300, 'bgr8'
        rgb.data = bytes(80 * 300)
        detector.on_rgb(rgb)
        end = time.monotonic() + .2
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
        key = rgb.header.stamp.sec*1_000_000_000 + rgb.header.stamp.nanosec
        matching = [event for event in events if event.get('capture_ns') == key]
        assert any(event['status'] == 'INPUT_RECEIVED' for event in matching)
        assert any(event['status'] == 'INPUT_REJECTED' and event['reason'] == 'FUTURE_CAPTURE'
                   for event in matching)
        assert detector.slot.take(0) is None
    finally:
        executor.shutdown()
        detector.destroy_node()
        peer.destroy_node()
        rclpy.shutdown()


def test_trace_keeps_capture_and_occurrence_time():
    rclpy.init(domain_id=146)
    detector, peer, executor = None, None, SingleThreadedExecutor()
    try:
        detector = ObjectDetector(parameter_overrides=[
            Parameter('backend', value='color_fixture'),
            Parameter('trace_enabled', value=True),
            Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8')])
        peer = Node('trace_detector_peer')
        executor.add_node(detector)
        executor.add_node(peer)
        traces, payloads, detections, sent = [], [], [], set()
        def received_trace(message):
            payloads.append(message.data)
            traces.append(json.loads(message.data))
        sub = peer.create_subscription(String, '/vision/detector_trace',
                                         received_trace, qos_profile_sensor_data)
        detected = peer.create_subscription(Detection2DArray, '/vision/detections',
                                             detections.append, qos_profile_sensor_data)
        image = np.zeros((80, 100, 3), np.uint8)
        image[10:30, 20:40, 2] = 255
        deadline = time.monotonic()+1.
        while time.monotonic() < deadline and not traces:
            t = peer.get_clock().now().nanoseconds/1e9
            calibration = info(t)
            calibration.width, calibration.height = 100, 80
            detector.on_info(calibration)
            rgb = stamp(Image(), t)
            rgb.width, rgb.height, rgb.step, rgb.encoding = 100, 80, 300, 'bgr8'
            rgb.data = image.tobytes()
            sent.add(rgb.header.stamp.sec*1_000_000_000+rgb.header.stamp.nanosec)
            detector.on_rgb(rgb)
            end = time.monotonic()+.04
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=.005)
        assert detections, 'original real ROS detection missing'
        assert traces, 'missing capture-linked detector trace'
        assert all(len(payload.encode('utf-8')) <= 4096 for payload in payloads)
        published = next(v for v in traces if v['outcome'] == 'PUBLISHED')
        assert published['source_frame'] == 'camera_optical_frame'
        assert published['capture_ns'] in sent
        assert published['ros_now_ns'] >= published['capture_ns']
        keys = ('rgb_receive', 'slot_put', 'work_take', 'convert_start', 'convert_end',
                'inference_start', 'inference_end', 'publish_start', 'publish_end')
        times = [published['times_ns'][k] for k in keys]
        assert times == sorted(times) and times[0] > 0
        assert detector.gate.max_age == .3
    finally:
        executor.shutdown(timeout_sec=2.)
        if detector is not None:
            detector.destroy_node()
        if peer is not None:
            peer.destroy_node()
        rclpy.try_shutdown()


def test_explicit_fifteen_hz_option_keeps_default_ten_and_single_worker():
    rclpy.init(domain_id=146)
    nodes = []
    try:
        default = ObjectDetector(parameter_overrides=[Parameter('backend', value='color_fixture')])
        nodes.append(default)
        assert default.rate == 10.
        max_age = default.gate.max_age
        default.destroy_node()
        nodes.clear()
        selected = ObjectDetector(parameter_overrides=[
            Parameter('backend', value='color_fixture'), Parameter('max_rate_hz', value=15.)])
        nodes.append(selected)
        assert selected.rate == 15. and selected.worker.is_alive()
        assert selected.gate.max_age == max_age == .3
    finally:
        for node in nodes:
            node.destroy_node()
        rclpy.try_shutdown()


@pytest.mark.parametrize('delay,should_publish', [(.15, True), (.35, False)])
@pytest.mark.parametrize('trace_enabled', [False, True])
def test_delayed_detector_capture_header_and_stale_completion(delay, should_publish, trace_enabled):
    rclpy.init(domain_id=146)
    detector, stimulus, executor = None, None, SingleThreadedExecutor()
    try:
        detector = ObjectDetector(parameter_overrides=[
            Parameter('backend', value='color_fixture'),
            Parameter('trace_enabled', value=trace_enabled),
            Parameter('trace_run_id', value='424240ff-0bfe-4a4b-92d4-93f6a78d49b8'),
            Parameter('processing_delay_s', value=delay)])
        stimulus = Node('detector_input_fixture')
        executor.add_node(detector)
        executor.add_node(stimulus)
        received, sent = [], set()
        diagnostics = []
        status_sub = stimulus.create_subscription(String, '/vision/detector_status',
                                                   lambda msg: diagnostics.append(msg.data), 10)
        sub = stimulus.create_subscription(Detection2DArray, '/vision/detections', received.append,
                                            qos_profile_sensor_data)
        rgb_pub = stimulus.create_publisher(Image, '/camera/color/image_raw', 5)
        info_pub = stimulus.create_publisher(CameraInfo, '/camera/color/camera_info', 5)
        image = np.zeros((80, 100, 3), np.uint8)
        image[10:30, 20:40, 2] = 255
        deadline = time.monotonic() + 1.2
        while time.monotonic() < deadline and not (should_publish and received):
            frame_deadline = time.monotonic() + 1/30
            t = stimulus.get_clock().now().nanoseconds/1e9
            calibration = info(t)
            calibration.width, calibration.height = 100, 80
            info_pub.publish(calibration)
            executor.spin_once(timeout_sec=.01)
            rgb = stamp(Image(), t)
            rgb.width, rgb.height, rgb.step, rgb.encoding = 100, 80, 300, 'bgr8'
            rgb.data = image.tobytes()
            sent.add((rgb.header.stamp.sec, rgb.header.stamp.nanosec))
            rgb_pub.publish(rgb)
            # spin_once returns immediately for ready callbacks: it is not a
            # frame-rate limiter. Generate an actual 30Hz camera fixture.
            while time.monotonic() < frame_deadline:
                executor.spin_once(timeout_sec=min(.005, frame_deadline-time.monotonic()))
        assert bool(received) is should_publish, f'inputs={len(sent)}, status={diagnostics[-10:]}'
        terminal = [json.loads(v) for v in diagnostics if json.loads(v)['status'] in
                    ('DETECTED', 'EXPIRED_BEFORE_INFERENCE')]
        assert terminal, diagnostics
        trace = terminal[-1]
        assert trace['capture_ns'] > 0
        assert trace['receipt_ros_age_s'] >= 0
        assert trace['queue_s'] >= 0 and trace['conversion_s'] >= 0
        assert trace['wall_age_s'] >= delay-.02
        assert trace['ros_age_s'] >= delay-.02
        assert trace['artificial_delay_s'] == delay
        if not should_publish:
            assert trace['wall_age_s'] > .3 or trace['ros_age_s'] > .3
        if should_publish:
            result = received[-1]
            assert (result.header.stamp.sec, result.header.stamp.nanosec) in sent
            assert result.header.frame_id == 'camera_optical_frame'
            assert result.detections[0].results[0].hypothesis.class_id == 'fixture_red'
            assert result.detections[0].bbox.center.position.x == 29.5
            age = stimulus.get_clock().now().nanoseconds/1e9 - (
                result.header.stamp.sec + result.header.stamp.nanosec/1e9)
            assert .1 <= age <= .3
    finally:
        executor.shutdown(timeout_sec=2)
        if detector is not None:
            detector.destroy_node()
            assert not detector.worker.is_alive()
        if stimulus is not None:
            stimulus.destroy_node()
        rclpy.try_shutdown()


def test_explicit_image_ingress_pause_discards_inflight_result_without_stopping_camera():
    rclpy.init(domain_id=146)
    detector, peer, executor = None, None, SingleThreadedExecutor()
    started, release = Event(), Event()
    try:
        detector = ObjectDetector(parameter_overrides=[Parameter('backend', value='color_fixture')])
        peer = Node('image_ingress_pause_peer')
        executor.add_node(detector)
        executor.add_node(peer)
        received = []
        sub = peer.create_subscription(Detection2DArray, '/vision/detections', received.append,
                                       qos_profile_sensor_data)
        toggle = peer.create_client(SetBool, '/object_detector/set_input_enabled')
        assert toggle.wait_for_service(timeout_sec=1.)
        original = detector.backend.detect

        def blocked(image):
            started.set()
            assert release.wait(timeout=1.)
            return original(image)

        detector.backend.detect = blocked
        t = peer.get_clock().now().nanoseconds/1e9
        calibration = info(t)
        calibration.width, calibration.height = 100, 80
        detector.on_info(calibration)
        image = np.zeros((80, 100, 3), np.uint8)
        image[10:30, 20:40, 2] = 255
        rgb = stamp(Image(), t)
        rgb.width, rgb.height, rgb.step, rgb.encoding = 100, 80, 300, 'bgr8'
        rgb.data = image.tobytes()
        detector.on_rgb(rgb)
        assert started.wait(timeout=.3)
        future = toggle.call_async(SetBool.Request(data=False))
        end = time.monotonic()+.3
        while not future.done() and time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
        assert future.done() and future.result().success
        release.set()
        end = time.monotonic()+.1
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
        assert received == [] and not detector.input_enabled
        # Pause is at perception ingress: native camera may keep publishing.
        detector.on_rgb(rgb)
        assert detector.slot.take(0) is None
        future = toggle.call_async(SetBool.Request(data=True))
        end = time.monotonic()+.3
        while not future.done() and time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
        assert future.done() and future.result().success and detector.input_enabled
        assert received == []  # unpause never republishes the old capture
    finally:
        release.set()
        executor.shutdown(timeout_sec=2.)
        if detector is not None:
            detector.destroy_node()
        if peer is not None:
            peer.destroy_node()
        rclpy.try_shutdown()
