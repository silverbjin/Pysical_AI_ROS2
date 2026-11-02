"""A native receiver must not re-enter Python polling for every DDS capture."""
import threading
import time
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from integrated_robot_interfaces.msg import FootContacts
from probe_navigation_13_5 import NavigationProbe,ProbeReceiver


def test_native_dispatch_does_not_poll_python_between_every_capture(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    peer=Node('native_continuous_dispatch_peer',context=context)
    pub=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    crossings={};old=threading.gettrace();receiver=None
    target=ProbeReceiver._spin.__code__
    def trace(frame,event,arg):
        if frame.f_code is target:
            if event=='line':
                ident=threading.get_ident();crossings[ident]=crossings.get(ident,0)+1
            return trace
        return None
    try:
        threading.settrace(trace);receiver=ProbeReceiver(probe)
        message=FootContacts();message.header.frame_id='odom'
        message.names=['fr_foot','fl_foot','rr_foot','rl_foot']
        # Discovery and the fixed workload are separate; retain every real receipt.
        end=time.monotonic()+2.
        while pub.get_subscription_count()!=1 and time.monotonic()<end:time.sleep(.005)
        assert pub.get_subscription_count()==1
        for index in range(120):
            message.header.stamp.sec=17;message.header.stamp.nanosec=index*1_000_000
            message.sequence=index;pub.publish(message);time.sleep(.006)
        end=time.monotonic()+1.
        while probe.callback_costs.get('_sensor:contacts',{}).get('count',0)<100 and time.monotonic()<end:time.sleep(.005)
        assert probe.callback_costs['_sensor:contacts']['count']>=100
        entered=crossings.get(receiver.ingress_receiver.thread.ident,0)
        assert entered<=40, f'native dispatch returned to Python polling {entered} times for the capture workload'
        latest=probe.inbox.pending['contacts'][17_119_000_000]
        assert latest.stamp_ns==17_119_000_000 and latest.received_ns>0
        assert receiver.shutdown(timeout_sec=2.)
        report=receiver.report()
        assert report['closed'] and report['recording']['closed'] and report['ingress']['closed']
        assert all(not row['thread_alive'] for row in (report,report['recording'],report['ingress']))
    finally:
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        threading.settrace(old)
        probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()
