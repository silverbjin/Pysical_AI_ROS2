"""Actual Jazzy delivers TF MessageInfo dictionaries as well as object APIs."""
from types import SimpleNamespace
from pathlib import Path
import sys

import pytest
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
from probe_navigation_13_5 import NavigationProbe


@pytest.mark.parametrize('mapping', [True, False])
def test_tf_publisher_identity_accepts_both_supported_message_info_shapes(mapping):
    record = SimpleNamespace(transforms=[], errors=[])
    transform = TransformStamped(child_frame_id='nav_base')
    transform.header.frame_id = 'odom'
    gid = [1, 2, 3, 4]
    info = {'publisher_gid': gid} if mapping else SimpleNamespace(publisher_gid=gid)
    NavigationProbe._tf(record, TFMessage(transforms=[transform]), info)
    assert record.transforms == [dict(parent='odom', child='nav_base', gid='01020304', stamp_ns=0)]
    assert not record.errors


def test_bad_tf_metadata_reports_fault_without_breaking_cleanup_executor():
    record = SimpleNamespace(transforms=[], errors=[])
    NavigationProbe._tf(record, TFMessage(), {})
    assert not record.transforms and record.errors


def test_actual_jazzy_metadata_capability_is_not_invented_as_a_publisher_identity():
    record = SimpleNamespace(transforms=[], errors=[], tf_api={})
    transform = TransformStamped(child_frame_id='nav_base')
    transform.header.frame_id = 'odom'
    NavigationProbe._tf(record, TFMessage(transforms=[transform]), {
        'source_timestamp': 123, 'received_timestamp': 124,
        'publication_sequence_number': 1, 'reception_sequence_number': None})
    assert not record.errors
    assert not record.transforms  # graph discovery is NOT per-message attribution
    assert record.tf_api['publisher_gid_available'] is False


def test_body_transport_trace_keeps_capture_and_clock_domains_separate(monkeypatch):
    from nav_msgs.msg import Odometry
    from integrated_robot_navigation.observations import SensorInbox
    import probe_navigation_13_5 as probe
    rows = []
    record = SimpleNamespace(engine='gazebo',body_references=[],inbox=SensorInbox(0), errors=[],
                             _write=lambda kind, value: rows.append((kind, value)))
    msg = Odometry(child_frame_id='base_footprint')
    msg.header.frame_id = 'odom'
    msg.header.stamp.sec = 1
    msg.pose.pose.orientation.w = 1.
    monkeypatch.setattr(probe.time, 'monotonic_ns', lambda: 2000)
    monkeypatch.setattr(probe.time, 'time_ns', lambda: 5000)
    NavigationProbe._sensor(record, 'body', msg, {
        'source_timestamp': 101, 'received_timestamp': 121})
    sample = next(value for kind, value in rows if kind == 'body')
    transport = next(value for kind, value in rows if kind == 'body_transport')
    assert sample['stamp_ns'] == 1_000_000_000 and sample['received_ns'] == 2000
    assert transport == dict(stamp_ns=1_000_000_000, received_ns=2000,
        callback_system_ns=5000, source_system_ns=101, rmw_received_system_ns=121)


def test_gazebo_body_reference_keeps_each_native_capture_independent_of_imu():
    from nav_msgs.msg import Odometry
    from integrated_robot_navigation.observations import SensorInbox
    record = SimpleNamespace(engine='gazebo',body_references=[],inbox=SensorInbox(0),errors=[],
        _write=lambda *_: None)
    msg = Odometry(child_frame_id='base_footprint')
    msg.header.frame_id = 'odom'
    msg.header.stamp.sec = 1
    msg.pose.pose.orientation.w = 1.
    msg.twist.twist.angular.x = .1
    NavigationProbe._sensor(record,'body',msg)
    msg.header.stamp.sec = 2
    msg.twist.twist.angular.x = .2
    NavigationProbe._sensor(record,'body',msg)
    assert record.body_references == [dict(capture_ns=i*1_000_000_000,epoch=0,
        sequence=i*1_000_000_000,frame_id='base_footprint',source='gazebo_native_odometry',
        angular_velocity=[value,0.,0.]) for i,value in [(1,.1),(2,.2)]]


def test_native_body_source_trace_matches_original_capture_without_republishing(monkeypatch):
    from mujoco_ros2_control_msgs.msg import FreeJointState, FreeJointStateArray
    import probe_navigation_13_5 as probe
    rows = []
    record = SimpleNamespace(transport_errors=[],
                             _write=lambda kind, value: rows.append((kind, value)))
    state = FreeJointState(name='base_link')
    state.pose.header.stamp.sec = 3
    state.pose.header.frame_id = ''
    state.pose.pose.orientation.w = 1.
    monkeypatch.setattr(probe.time, 'monotonic_ns', lambda: 4000)
    monkeypatch.setattr(probe.time, 'time_ns', lambda: 7000)
    NavigationProbe._body_source(record, FreeJointStateArray(free_joints=[state]), {
        'source_timestamp': 201, 'received_timestamp': 221})
    assert rows == [('body_source', dict(stamp_ns=3_000_000_000, received_ns=4000,
        callback_system_ns=7000, source_system_ns=201, rmw_received_system_ns=221))]
    assert not record.transport_errors


def test_native_controls_record_keeps_source_capture_and_actual_ctrl(monkeypatch):
    import json
    from std_msgs.msg import String
    import probe_navigation_13_5 as probe
    rows = []
    record = SimpleNamespace(engine='mujoco', stage='stand', native_controls=[], transport_errors=[],
                             _write=lambda kind, value: rows.append((kind, value)))
    payload = dict(schema=1, capture_ns=123, epoch=0, sequence=7,
                   actuators=[dict(joint_name='fr_hip_joint', ctrl=.1, position=.09)])
    monkeypatch.setattr(probe.time, 'monotonic_ns', lambda: 4000)
    NavigationProbe._controls(record, String(data=json.dumps(payload)))
    assert record.native_controls == [dict(**payload, received_ns=4000, stage='stand')]
    assert rows == [('native_controls', record.native_controls[0])]
    assert not record.transport_errors


def test_gazebo_controls_actual_dds_subscription_preserves_distinct_native_schema(tmp_path):
    import json
    import time
    import rclpy
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import QoSProfile
    from std_msgs.msg import String
    context = Context()
    rclpy.init(context=context)
    executor = SingleThreadedExecutor(context=context)
    receiver = NavigationProbe(tmp_path, engine='gazebo', context=context)
    source = Node('native_controls_test_producer', context=context)
    executor.add_node(receiver)
    executor.add_node(source)
    # Match the installed bridge's actually discovered RELIABLE offer.
    pub = source.create_publisher(String, '/navigation/native_controls', QoSProfile(depth=100))
    payload = dict(schema=2, engine='gazebo', capture_ns=123000000, epoch=0, sequence=7,
        joints=[dict(name='fr_hip_joint', position=.12, velocity=-.3, velocity_command=-.7,
                     projected_transmitted_effort=-2.5, applied_generalized_force=None)])
    try:
        deadline = time.monotonic()+5.
        while time.monotonic() < deadline and not receiver.native_controls:
            pub.publish(String(data=json.dumps(payload)))
            executor.spin_once(timeout_sec=.05)
        assert receiver.native_controls, 'Gazebo native command diagnostics were not received'
        first = receiver.native_controls[0]
        assert first['capture_ns'] == 123000000 and first['sequence'] == 7
        assert first['joints'][0]['velocity_command'] == -.7
        assert first['joints'][0]['projected_transmitted_effort'] == -2.5
        assert first['joints'][0]['applied_generalized_force'] is None
        assert not receiver.transport_errors
    finally:
        executor.shutdown()
        receiver.close_log()
        receiver.destroy_node()
        source.destroy_node()
        rclpy.try_shutdown(context=context)


@pytest.mark.parametrize('engine,payload', [
    ('gazebo', dict(schema=1, capture_ns=12, epoch=0, sequence=3, actuators=[])),
    ('mujoco', dict(schema=2, engine='gazebo', capture_ns=12, epoch=0, sequence=3, joints=[])),
    ('gazebo', dict(schema=2, engine='mujoco', capture_ns=12, epoch=0, sequence=3, joints=[])),
])
def test_native_controls_do_not_mislabel_another_backend_schema(engine, payload):
    import json
    from std_msgs.msg import String
    record = SimpleNamespace(engine=engine, stage='stand', native_controls=[], transport_errors=[],
                             _write=lambda *_: None)
    NavigationProbe._controls(record, String(data=json.dumps(payload)))
    assert not record.native_controls
    assert record.transport_errors
