"""Actual callback signatures and DDS timestamps, not physical acceptance."""
from pathlib import Path
import sys
import time
import json

import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from mujoco_ros2_control_msgs.msg import FreeJointState, FreeJointStateArray

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
from probe_navigation_13_5 import NavigationProbe


def test_actual_body_source_and_adapter_output_have_separate_transport_records(tmp_path):
    context = Context()
    rclpy.init(context=context)
    peer = rclpy.create_node('body_transport_peer', context=context)
    probe = NavigationProbe(tmp_path, context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(peer)
    executor.add_node(probe)
    records = []
    original_write = probe._write

    def record(kind, value):
        records.append((kind, value))
        original_write(kind, value)

    probe._write = record
    source = peer.create_publisher(FreeJointStateArray, '/native/free_joint_states', 10)
    body = peer.create_publisher(Odometry, '/odom', 10)
    controls = peer.create_publisher(String, '/navigation/native_controls', 10)
    state = FreeJointState(name='base_link')
    state.pose.header.stamp.sec = 1
    state.pose.pose.orientation.w = 1.
    odom = Odometry(child_frame_id='base_footprint')
    odom.header.stamp.sec, odom.header.frame_id = 1, 'odom'
    odom.pose.pose.orientation.w = 1.
    try:
        deadline = time.monotonic()+3.
        while not {'body_source', 'body_transport', 'native_controls'} <= {kind for kind, _ in records}:
            assert time.monotonic() < deadline
            source.publish(FreeJointStateArray(free_joints=[state]))
            body.publish(odom)
            controls.publish(String(data=json.dumps(dict(schema=1, capture_ns=1_000_000_000,
                epoch=0, sequence=1, actuators=[dict(joint_name='fr_hip_joint', ctrl=.1)]))))
            executor.spin_once(timeout_sec=.01)
        for kind in ('body_source', 'body_transport'):
            actual = next(value for key, value in records if key == kind)
            assert actual['stamp_ns'] == 1_000_000_000
            assert actual['received_ns'] > 0
            assert actual['callback_system_ns'] > 0
            assert actual['source_system_ns'] > 0
            assert actual['rmw_received_system_ns'] > 0
        assert not probe.errors and not probe.transport_errors
        assert probe.native_controls[0]['capture_ns'] == 1_000_000_000
        assert probe.native_controls[0]['actuators'][0]['ctrl'] == .1
        assert probe.count_publishers('/leg_position_controller/commands') == 0
        assert probe.count_publishers('/navigation/cmd_vel') == 0
    finally:
        executor.shutdown(timeout_sec=2.)
        probe.close_log()
        probe.destroy_node()
        peer.destroy_node()
        context.try_shutdown()
