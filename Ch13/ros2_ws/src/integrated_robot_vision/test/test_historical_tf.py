"""Real tf2 Buffer tests, not a fake lookup that ignores requested time."""
import numpy as np
import pytest
import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformException

from integrated_robot_vision.vision_processor import lookup_capture_point, capture_observations
from integrated_robot_vision.contracts import Box2D
from test_rgbd_cache import populated


@pytest.fixture
def buffer():
    rclpy.init()
    buffer = Buffer()
    for sec, nanosec, x in [(1, 0, 0.), (1, 150_000_000, 1.)]:
        transform = TransformStamped()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'camera_optical_frame'
        transform.header.stamp = Time(sec=sec, nanosec=nanosec)
        transform.transform.rotation.w = 1.
        transform.transform.translation.x = x
        buffer.set_transform(transform, 'captured_engine_pose')
    yield buffer
    rclpy.shutdown()


def test_capture_transform_is_not_latest_and_preserves_stamp(buffer):
    stamp = Time(sec=1)
    result = lookup_capture_point(buffer, np.array([0, 0, 1.]), 'camera_optical_frame', stamp)
    assert result.header.frame_id == 'odom'
    assert result.header.stamp == stamp
    assert [result.point.x, result.point.y, result.point.z] == [0., 0., 1.]


def test_zero_disconnected_and_out_of_range_never_use_latest(buffer):
    with pytest.raises(ValueError):
        lookup_capture_point(buffer, np.ones(3), 'camera_optical_frame', Time())
    with pytest.raises(TransformException):
        lookup_capture_point(buffer, np.ones(3), 'missing', Time(sec=1))
    with pytest.raises(TransformException):
        lookup_capture_point(buffer, np.ones(3), 'camera_optical_frame', Time(sec=2))


def test_observation_that_expires_during_lookup_is_discarded(buffer):
    bundle = populated().match(1., 'camera_optical_frame', 0)
    checks = iter([True, True, False])
    assert capture_observations(bundle, [Box2D(5, 5, 6, 6, 'x', .9)], buffer,
                                still_valid=lambda: next(checks, False)) == []
