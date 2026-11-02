"""Break: flattening a 6D observation without rotating its body-frame twist."""
from copy import deepcopy
from dataclasses import replace
import importlib
import math

import pytest
from integrated_robot_navigation.samples import Sample


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.projection'), 'projection missing'
    return importlib.import_module('integrated_robot_navigation.projection')


def test_projection_preserves_capture_and_6d_input_but_changes_twist_basis():
    r, p, y = .3, .4, math.pi/2
    sr, cr, sp, cp, sy, cy = (math.sin(r/2), math.cos(r/2), math.sin(p/2),
                              math.cos(p/2), math.sin(y/2), math.cos(y/2))
    quaternion = (sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy,
                  cr*cp*sy-sr*sp*cy, cr*cp*cy+sr*sp*sy)
    source = Sample(1_000_000_000, 10_000_000_000, 3, 7, 'odom', dict(
        position=(1., 2., .46), orientation=quaternion,
        linear_velocity=(1., 0., 0.), angular_velocity=(0., 0., 1.),
        child_frame_id='base_footprint'))
    original = deepcopy(source)
    result = api().project_body(source)
    assert source == original and result.stamp_ns == source.stamp_ns
    assert (result.received_ns, result.epoch, result.sequence) == (source.received_ns, 3, 7)
    assert result.frame_id == 'odom' and result.data['child_frame_id'] == 'nav_base'
    assert result.data['position'] == (1., 2., 0.)
    assert result.data['orientation'] == pytest.approx((0., 0., math.sqrt(.5), math.sqrt(.5)))
    assert result.data['linear_velocity'] == pytest.approx((math.cos(.4), 0., 0.))
    assert result.data['angular_velocity'] == pytest.approx((0., 0., math.cos(.3)/math.cos(.4)))


@pytest.mark.parametrize('field,value', [('orientation', (0., 0., 0., 0.)),
                                       ('position', (0., 0., math.nan))])
def test_bad_native_observation_is_not_projected(field, value):
    source = Sample(1, 2, 0, 1, 'odom', dict(position=(0., 0., .4),
        orientation=(0., 0., 0., 1.), linear_velocity=(0.,)*3, angular_velocity=(0.,)*3,
        child_frame_id='base_footprint'))
    with pytest.raises(ValueError):
        api().project_body(replace(source, data={**source.data, field: value}))


def test_actual_dds_projection_has_only_new_odom_and_tf_ownership():
    module = api()
    assert hasattr(module, 'NavProjection'), 'projection ROS node not available'
    import time
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from nav_msgs.msg import Odometry
    from tf2_msgs.msg import TFMessage
    ctx = Context()
    rclpy.init(context=ctx)
    node = module.NavProjection(context=ctx)
    peer = Node('projection_observer_test', context=ctx)
    executor = SingleThreadedExecutor(context=ctx)
    executor.add_node(node)
    executor.add_node(peer)
    outputs, transforms = [], []
    pub = peer.create_publisher(Odometry, '/odom', 10)
    sub = peer.create_subscription(Odometry, '/navigation/odom', outputs.append, 10)
    tf_sub = peer.create_subscription(TFMessage, '/tf', lambda msg: transforms.extend(msg.transforms), 10)
    source = Odometry(child_frame_id='base_footprint')
    source.header.frame_id, source.header.stamp.sec = 'odom', 4
    source.pose.pose.position.x, source.pose.pose.position.z = 1., .46
    source.pose.pose.orientation.x, source.pose.pose.orientation.w = math.sin(.2), math.cos(.2)
    original = deepcopy(source)
    try:
        deadline = time.monotonic()+2.
        while (not outputs or not transforms) and time.monotonic() < deadline:
            pub.publish(source)
            for _ in range(5):
                executor.spin_once(timeout_sec=.002)
        assert outputs and transforms
        assert peer.count_publishers('/odom') == 1
        assert outputs[-1].header == source.header and outputs[-1].child_frame_id == 'nav_base'
        assert outputs[-1].pose.pose.position.z == 0.
        assert outputs[-1].pose.covariance[14] > 1000.
        assert {t.child_frame_id for t in transforms} == {'nav_base'}
        assert all(t.header == source.header and t.transform.translation.z == 0. for t in transforms)
        assert source == original
    finally:
        executor.shutdown(timeout_sec=2.)
        node.destroy_node()
        peer.destroy_node()
        ctx.try_shutdown()
