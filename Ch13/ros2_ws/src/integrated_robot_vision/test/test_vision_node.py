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
