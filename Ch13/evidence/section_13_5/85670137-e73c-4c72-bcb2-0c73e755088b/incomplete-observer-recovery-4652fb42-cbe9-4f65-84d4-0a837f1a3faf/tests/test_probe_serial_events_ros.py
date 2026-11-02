"""Actual probe receiver metadata, sticky callback failure and resource join.

Native 305db3ec is the timing RED. This test protects communication/lifetime
while reusing the already reviewed serial event backend, not physical success.
"""
import json
import threading
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from integrated_robot_interfaces.msg import FootContacts
from probe_navigation_13_5 import NavigationProbe,ProbeReceiver


def test_actual_probe_receiver_keeps_native_metadata_and_sticky_failure_before_join(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    peer=Node('serial_probe_timing_peer',context=context);receiver=ProbeReceiver(probe)
    publisher=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    records=[];entered=threading.Event()
    original=probe._write
    def record(kind,value):
        original(kind,value)
        if kind=='contacts_transport':records.append(value)
    probe._write=record
    try:
        message=FootContacts();message.header.stamp.sec=1;message.header.frame_id='odom';message.sequence=77
        message.names=['fr_foot','fl_foot','rr_foot','rl_foot']
        deadline=time.monotonic()+2.
        while not records and time.monotonic()<deadline:
            publisher.publish(message);time.sleep(.005)
        receiver.check();assert records,'serial receiver lost native FootContacts/MessageInfo'
        value=records[0]
        assert value['stamp_ns']==1_000_000_000 and value['native_sequence']==77
        assert value['source_system_ns']>0 and value['rmw_received_system_ns']>0
        def fail():entered.set();raise ValueError('selected serial receiver callback failure')
        probe.create_timer(.01,fail,clock=Clock(clock_type=ClockType.STEADY_TIME))
        assert entered.wait(1.)
        deadline=time.monotonic()+1.
        while receiver.thread.is_alive() and time.monotonic()<deadline:time.sleep(.005)
        with pytest.raises(RuntimeError,match='callback failed'):receiver.check()
        assert receiver.shutdown(timeout_sec=2.) and not receiver.thread.is_alive()
        with pytest.raises(RuntimeError,match='callback failed'):receiver.check()
    finally:
        assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()
