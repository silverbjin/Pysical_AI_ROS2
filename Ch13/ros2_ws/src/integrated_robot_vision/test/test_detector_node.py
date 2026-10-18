"""Real ROS delayed inference must retain capture time and reject expired jobs."""
import time

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
