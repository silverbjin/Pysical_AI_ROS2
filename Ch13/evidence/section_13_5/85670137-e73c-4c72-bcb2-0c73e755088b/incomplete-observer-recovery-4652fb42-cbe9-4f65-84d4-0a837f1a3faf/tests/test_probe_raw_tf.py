"""Avoid unused TF object conversion without inventing authority or timestamps."""
import threading
import time
from types import SimpleNamespace

import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.serialization import serialize_message, deserialize_message
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
from probe_navigation_13_5 import NavigationProbe, ProbeReceiver


def test_bounded_probe_receives_original_tf_bytes_before_metadata_admission(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    peer=Node('raw_tf_boundary_peer',context=context)
    publisher=peer.create_publisher(TFMessage,'/tf',qos_profile_sensor_data)
    seen=[];arrived=threading.Event();original=probe._tf
    def receive(message,info):
        seen.append((message,info));original(message,info);arrived.set()
    probe._tf=receive
    receiver=ProbeReceiver(probe)
    message=TFMessage(transforms=[TransformStamped(child_frame_id='fixture_child')])
    message.transforms[0].header.frame_id='fixture_parent'
    message.transforms[0].header.stamp.sec=17
    message.transforms[0].transform.rotation.w=1.
    try:
        end=time.monotonic()+2.
        while not arrived.is_set() and time.monotonic()<end:
            publisher.publish(message);time.sleep(.01)
        receiver.check();assert seen,'DDS TF callback missing'
        assert isinstance(seen[0][0],bytes),'TF was converted before authority admission'
        # Separate CDR encodings may have different padding bytes. Check the
        # received payload's original fields, not unspecified padding memory.
        assert deserialize_message(seen[0][0],TFMessage)==message,'capture or TF fields changed'
        info=seen[0][1]
        assert info['source_timestamp']>0 and info['received_timestamp']>0
        if 'publisher_gid' not in info:
            assert not probe.transforms and not probe.errors
            assert probe.tf_api['authority_source']=='required_native_cpp_observer'
    finally:
        assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()


def test_available_tf_identity_deserializes_original_capture_and_links():
    record=SimpleNamespace(_lock=threading.RLock(),transforms=[],errors=[],bounded_history=False)
    message=TFMessage(transforms=[TransformStamped(child_frame_id='child')])
    message.transforms[0].header.frame_id='parent'
    message.transforms[0].header.stamp.sec=17
    NavigationProbe._tf(record,serialize_message(message),{'publisher_gid':[1,2,3]})
    assert record.transforms==[dict(parent='parent',child='child',gid='010203',stamp_ns=17_000_000_000)]
    assert not record.errors


def test_bad_serialized_tf_with_identity_is_visible_failure():
    record=SimpleNamespace(_lock=threading.RLock(),transforms=[],errors=[],bounded_history=False)
    NavigationProbe._tf(record,b'broken',{'publisher_gid':[1,2,3]})
    assert not record.transforms and record.errors
