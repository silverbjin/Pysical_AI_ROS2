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


@pytest.mark.parametrize('delay,should_publish', [(.15, True), (.35, False)])
def test_delayed_detector_capture_header_and_stale_completion(delay, should_publish):
    rclpy.init(domain_id=146)
    detector, stimulus, executor = None, None, SingleThreadedExecutor()
    try:
        detector = ObjectDetector(parameter_overrides=[
            Parameter('backend', value='color_fixture'),
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
        rgb_pub = stimulus.create_publisher(Image, '/camera/color/image_raw', qos_profile_sensor_data)
        info_pub = stimulus.create_publisher(CameraInfo, '/camera/color/camera_info', qos_profile_sensor_data)
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
