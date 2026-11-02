"""Actual DDS timing separates capture, publisher, middleware and callback."""
import json
import time
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from integrated_robot_interfaces.msg import FootContacts
from std_msgs.msg import String
from probe_navigation_13_5 import NavigationProbe


def test_g2_probe_preserves_native_lease_id_and_dds_timing_for_both_streams(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='mujoco',bounded_history=True,context=context)
    peer=Node('native_sensor_timing_peer',context=context)
    executor=SingleThreadedExecutor(context=context);executor.add_node(probe);executor.add_node(peer)
    # This fixture tests message metadata, not the native receiver scheduler.
    # Explicitly own both clockless observer nodes' subscriptions too.
    executor.add_node(probe.recording_node)
    executor.add_node(probe.ingress_node)
    feet=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    controls=peer.create_publisher(String,'/navigation/native_controls',100)
    rows=[];probe._write=lambda kind,value:rows.append((kind,value))
    try:
        message=FootContacts();message.header.stamp.sec=1;message.header.frame_id='odom'
        message.names=['fr_foot','fl_foot','rr_foot','rl_foot'];message.sequence=77
        deadline=time.monotonic()+2.
        while not {'contacts_transport','native_controls_transport'}<={k for k,_ in rows} and time.monotonic()<deadline:
            feet.publish(message)
            controls.publish(String(data=json.dumps(dict(schema=1,capture_ns=1_000_000_000,epoch=0,sequence=77,actuators=[]))))
            executor.spin_once(timeout_sec=.005)
        for kind in ('contacts_transport','native_controls_transport'):
            matches=[value for key,value in rows if key==kind]
            assert matches,kind+' lost DDS timing; capture age cannot locate the delay boundary'
            value=matches[0]
            assert value['stamp_ns']==1_000_000_000 and value['native_sequence']==77 and value['epoch']==0
            assert value['received_ns']>0 and value['callback_system_ns']>0
            assert value['source_system_ns']>0 and value['rmw_received_system_ns']>0
        assert probe.inbox.pending['contacts'][1_000_000_000].sequence==1_000_000_000, \
            'native lease identity must not silently replace normalized snapshot semantics'
    finally:
        executor.shutdown();probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()
