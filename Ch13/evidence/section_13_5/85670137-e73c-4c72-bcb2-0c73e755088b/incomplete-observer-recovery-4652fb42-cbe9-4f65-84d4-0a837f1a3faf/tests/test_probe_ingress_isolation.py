"""Native input queue must not share control/clock/RPC head-of-line waits."""
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


def test_native_ingress_keeps_original_receipts_while_main_queue_waits(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    peer=Node('isolated_probe_input_peer',context=context)
    publisher=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    entered,release=threading.Event(),threading.Event();receiver=None
    def blocked():
        timer.cancel();entered.set();assert release.wait(3.)
    timer=probe.create_timer(.01,blocked,clock=Clock(clock_type=ClockType.STEADY_TIME))
    try:
        receiver=ProbeReceiver(probe);assert entered.wait(1.)
        message=FootContacts();message.header.frame_id='odom'
        message.names=['fr_foot','fl_foot','rr_foot','rl_foot']
        sent=time.monotonic_ns();message.header.stamp.sec=17;message.sequence=77
        deadline=time.monotonic()+.15;selected=None
        while time.monotonic()<deadline:
            publisher.publish(message);time.sleep(.005)
            with probe._lock:selected=probe.inbox.pending['contacts'].get(17_000_000_000)
            if selected is not None:break
        assert selected is not None,'native capture waited behind the blocked main queue'
        assert sent<=selected.received_ns<=time.monotonic_ns()
        assert time.monotonic_ns()-selected.received_ns<100_000_000
        assert selected.stamp_ns==17_000_000_000
        assert not probe.frames,'isolated input is not synthetic complete physics feedback'
        assert sum(s.topic_name=='/clock' for n in (probe,probe.ingress_node,probe.recording_node) for s in n.subscriptions)==1
        assert not any(s.topic_name=='/clock' for s in probe.ingress_node.subscriptions)
    finally:
        release.set()
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()


def test_unfinished_ingress_retains_all_ros_resources_and_failure_is_sticky(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    entered,release=threading.Event(),threading.Event();receiver=None
    try:
        assert getattr(probe,'ingress_node',None) is not None
        def blocked():entered.set();assert release.wait(3.);raise ValueError('native ingress fault fixture')
        probe.ingress_node.create_timer(.01,blocked,clock=Clock(clock_type=ClockType.STEADY_TIME))
        receiver=ProbeReceiver(probe);assert entered.wait(1.)
        assert not receiver.shutdown(timeout_sec=.01)
        assert not receiver.closed and receiver.ingress_receiver.thread.is_alive()
        assert probe.ingress_node.context.ok()
        release.set()
        assert receiver.shutdown(timeout_sec=2.)
        with pytest.raises(RuntimeError,match='native ingress fault fixture'):receiver.check()
        report=receiver.report()
        assert report['closed'] and report['ingress']['closed'] and report['recording']['closed']
        assert not report['ingress']['thread_alive'] and not report['recording']['thread_alive']
    finally:
        release.set()
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_first_receipt_precedes_a_blocked_inbox_lock(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    peer=Node('inbox_receipt_peer',context=context)
    publisher=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    entered=threading.Event();entries=[];original=probe._dispatch
    def dispatch(callback,*args):
        if callback.__name__=='_sensor' and args[0]=='contacts':
            entries.append(time.monotonic_ns());entered.set()
        return original(callback,*args)
    probe._dispatch=dispatch;receiver=ProbeReceiver(probe);held=False
    try:
        probe._lock.acquire();held=True
        message=FootContacts();message.header.frame_id='odom';message.header.stamp.sec=17
        end=time.monotonic()+1.
        while not entered.is_set() and time.monotonic()<end:
            publisher.publish(message);time.sleep(.005)
        assert entered.is_set();time.sleep(.12)
        released=time.monotonic_ns();probe._lock.release();held=False
        end=time.monotonic()+1.;sample=None
        while sample is None and time.monotonic()<end:
            with probe._lock:sample=probe.inbox.pending['contacts'].get(17_000_000_000)
            time.sleep(.005)
        assert sample is not None
        assert entries[0]<=sample.received_ns<released,'inbox wait renewed the original receipt'
    finally:
        if held:probe._lock.release()
        assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()


def test_decision_projection_cannot_hold_sensor_ingress_lock(tmp_path,monkeypatch):
    from rosgraph_msgs.msg import Clock as ClockMessage
    from builtin_interfaces.msg import Time
    from nav_msgs.msg import Odometry
    import integrated_robot_navigation.g2_sequence as sequence
    from integrated_robot_navigation.carry_profile import default_limits
    context=Context();rclpy.init(context=context)
    peer=Node('movement_snapshot_input_peer',context=context)
    clock=peer.create_publisher(ClockMessage,'/clock',10)
    body=peer.create_publisher(Odometry,'/odom',qos_profile_sensor_data)
    contacts=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    stop=threading.Event()
    def publish():
        origin=time.monotonic_ns()
        while not stop.is_set():
            stamp_ns=1_000_000_000+time.monotonic_ns()-origin
            stamp=Time(sec=stamp_ns//1_000_000_000,nanosec=stamp_ns%1_000_000_000)
            odom=Odometry(child_frame_id='base_footprint');odom.header.frame_id='odom';odom.header.stamp=stamp
            odom.pose.pose.orientation.w=1.;odom.pose.pose.position.z=.46
            feet=FootContacts();feet.header.frame_id='odom';feet.header.stamp=stamp;feet.touching=[True]*4
            clock.publish(ClockMessage(clock=stamp));body.publish(odom);contacts.publish(feet);time.sleep(.01)
    publisher=threading.Thread(target=publish);publisher.start()
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    receiver=ProbeReceiver(probe);entered,release=threading.Event(),threading.Event();worker=None;out=[]
    original=sequence.movement_snapshot
    def blocked(*args):
        entered.set();assert release.wait(3.)
        return original(*args)
    try:
        end=time.monotonic()+2.;first=None
        while first is None and time.monotonic()<end:
            with probe._lock:first=probe.inbox.bundle(probe.get_clock().now().nanoseconds).body
            time.sleep(.005)
        assert first is not None
        monkeypatch.setattr(sequence,'movement_snapshot',blocked)
        def decide():
            try:out.append(probe.movement_decision(default_limits()))
            except BaseException as error:out.append(error)
        worker=threading.Thread(target=decide);worker.start();assert entered.wait(1.)
        time.sleep(.15)
        acquired=probe._lock.acquire(timeout=.05)
        assert acquired,'decision projection held the sensor ingress lock'
        try:latest=probe.inbox.bundle(probe.get_clock().now().nanoseconds).body
        finally:probe._lock.release()
        assert latest.stamp_ns>first.stamp_ns
        release.set();worker.join(2.);assert not worker.is_alive()
        assert out and isinstance(out[0],dict)
        assert out[0]['capture_ns']<=latest.stamp_ns,'snapshot was replaced with a later capture'
    finally:
        release.set()
        if worker:worker.join(2.)
        assert receiver.shutdown(timeout_sec=2.)
        stop.set();publisher.join(2.);assert not publisher.is_alive()
        probe.close_log();probe.destroy_node();peer.destroy_node();context.try_shutdown()
