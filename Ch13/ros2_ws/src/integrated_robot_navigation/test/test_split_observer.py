"""The full evidence observer is independent; no per-capture IPC is needed."""
import importlib
import importlib.util
import inspect
import json
import os
import time
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from integrated_robot_interfaces.msg import FootContacts
from probe_navigation_13_5 import NavigationProbe


def api():
    assert importlib.util.find_spec('split_observer_13_5') is not None,'independent full observer missing'
    return importlib.import_module('split_observer_13_5')


def test_full_observer_owns_ros_recording_and_closes_without_capture_ipc(tmp_path):
    module=api();context=Context();rclpy.init(context=context)
    peer=Node('full_observer_fixture_peer',context=context)
    pub=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    owner=module.ObserverProcess(tmp_path,engine='gazebo')
    try:
        assert owner.identity['pid']!=os.getpid() and owner.identity['uid']==os.getuid()
        owner.set_stage('stand')
        end=time.monotonic()+3.
        while pub.get_subscription_count()!=1 and time.monotonic()<end:time.sleep(.01)
        assert pub.get_subscription_count()==1
        msg=FootContacts();msg.header.frame_id='odom';msg.names=['fr_foot','fl_foot','rr_foot','rl_foot']
        for i in range(30):
            msg.header.stamp.sec=17;msg.header.stamp.nanosec=i*1_000_000;msg.sequence=i;pub.publish(msg);time.sleep(.01)
        data=owner.finish(timeout_sec=10.)
        report=owner.report()
        assert report['joined'] and report['exitcode']==0 and report['receiver']['closed']
        assert report['ipc_requests']==2,'captures crossed the process boundary instead of staying in their ROS/file owner'
        rows=[json.loads(line) for line in (tmp_path/'observations.jsonl').read_text().splitlines()]
        contacts=[r['value'] for r in rows if r['kind']=='contacts']
        assert len(contacts)>=20 and contacts[-1]['stamp_ns']==17_029_000_000
        assert contacts[-1]['received_ns']>0
        assert data['frames']==[],'an incomplete fixture became physical evidence'
        assert not data['errors']
    finally:
        owner.finish(timeout_sec=10.)
        peer.destroy_node();context.try_shutdown()


def test_mission_observer_keeps_original_clock_and_only_its_required_sensors(tmp_path):
    assert 'mission_only' in inspect.signature(NavigationProbe).parameters,'minimal mission ingress missing'
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,mission_only=True,context=context)
    try:
        topics={s.topic_name for node in (probe,probe.ingress_node) for s in node.subscriptions}
        assert {'/clock','/odom','/navigation/foot_contacts'}<=topics
        assert not topics.intersection(('/joint_states','/navigation/imu','/scan','/tf','/navigation/native_controls'))
        assert probe.recording_node is None and probe.get_name()=='navigation_mission_probe'
        assert not {p.topic_name for p in probe.publishers}.intersection((
            '/navigation/cmd_vel','/navigation/cmd_vel_raw','/navigation/cmd_vel_smoothed',
            '/leg_position_controller/commands','/arm_controller/joint_trajectory'))
    finally:
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_parent_connection_loss_is_sticky_and_does_not_restart_observer(tmp_path):
    import pytest
    owner=api().ObserverProcess(tmp_path,engine='gazebo');pid=owner.identity['pid']
    owner.connection.close()
    with pytest.raises(RuntimeError):owner.finish(timeout_sec=10.)
    assert owner.report()['joined'] and owner.report()['exitcode']!=0
    assert owner.identity['pid']==pid
    with pytest.raises(RuntimeError):owner.finish(timeout_sec=10.)


def test_split_mission_uses_its_original_receipts_then_imports_joined_full_evidence(tmp_path):
    import threading
    from builtin_interfaces.msg import Time
    from rosgraph_msgs.msg import Clock
    from nav_msgs.msg import Odometry
    from integrated_robot_navigation.carry_profile import default_limits
    module=api();context=Context();rclpy.init(context=context)
    peer=Node('split_mission_input_peer',context=context)
    clock=peer.create_publisher(Clock,'/clock',10)
    body=peer.create_publisher(Odometry,'/odom',qos_profile_sensor_data)
    feet=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    stop=threading.Event()
    def publish():
        start=time.monotonic_ns()
        while not stop.is_set():
            now=1_000_000_000+time.monotonic_ns()-start;stamp=Time(sec=now//1_000_000_000,nanosec=now%1_000_000_000)
            msg=Odometry(child_frame_id='base_footprint');msg.header.frame_id='odom';msg.header.stamp=stamp;msg.pose.pose.orientation.w=1.;msg.pose.pose.position.z=.46
            contact=FootContacts();contact.header.frame_id='odom';contact.header.stamp=stamp;contact.touching=[True]*4
            clock.publish(Clock(clock=stamp));body.publish(msg);feet.publish(contact);stop.wait(.01)
    publisher=threading.Thread(target=publish);probe=receiver=None
    try:
        probe=module.SplitNavigationProbe(tmp_path,engine='gazebo',context=context);receiver=module.ProbeReceiver(probe)
        publisher.start()
        probe.set_stage('stand');end=time.monotonic()+2.;sample=None
        while sample is None and time.monotonic()<end:
            with probe._lock:sample=probe.inbox.bundle(probe.get_clock().now().nanoseconds).body
            time.sleep(.01)
        assert sample is not None
        result=probe.movement_decision(default_limits())
        assert result['capture_ns']>0 and result['stage']=='stand'
        with probe._lock:assert time.monotonic_ns()-probe.inbox.samples['body'].received_ns<200_000_000
        assert receiver.shutdown(timeout_sec=2.)
        probe.restore_history(receiver_joined=True)
        assert probe.full_restored and probe.observer.report()['joined'] and probe.observer.report()['exitcode']==0
        assert probe.frames==[],'incomplete source was accepted as full engine evidence'
        assert (tmp_path/'mission_probe/observations.jsonl').exists()
        assert (tmp_path/'observations.jsonl').exists()
        rows=[json.loads(line) for line in (tmp_path/'mission_probe/observations.jsonl').read_text().splitlines()]
        decision=[row['value'] for row in rows if row['kind']=='movement_decision'][-1]
        assert result['capture_ns']==min(decision['samples'][key]['stamp_ns'] for key in ('body','contacts'))
    finally:
        stop.set()
        if publisher.is_alive():publisher.join(2.)
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        if probe:
            if not probe.full_restored:probe.restore_history(receiver_joined=True)
            probe.close_log();probe.destroy_node()
        peer.destroy_node();context.try_shutdown()


def test_runner_factory_uses_distinct_mission_and_full_witness_owners(tmp_path):
    import run_navigation_13_5 as runner
    assert hasattr(runner,'make_native_probe'),'native runner still constructs one shared interpreter observer'
    context=Context();rclpy.init(context=context)
    probe=runner.make_native_probe(tmp_path,engine='gazebo',context=context)
    receiver=api().ProbeReceiver(probe)
    try:
        assert probe.get_name()=='navigation_mission_probe'
        assert probe.observer.identity['pid']!=os.getpid()
        assert probe.observer.identity['module_files']==api()._modules()
        assert receiver.shutdown(timeout_sec=2.)
        probe.restore_history(receiver_joined=True)
        assert probe.observer.report()['joined'] and probe.observer.report()['exitcode']==0
    finally:
        assert receiver.shutdown(timeout_sec=2.)
        if not probe.full_restored:probe.restore_history(receiver_joined=True)
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_runtime_motion_fault_does_not_block_recording_cleanup_or_erase_evidence(tmp_path):
    import pytest
    from integrated_robot_interfaces.msg import MotionState
    context=Context();rclpy.init(context=context);peer=Node('observer_runtime_fault_peer',context=context)
    publisher=peer.create_publisher(MotionState,'/navigation/carry_state',10)
    owner=api().ObserverProcess(tmp_path,engine='gazebo');seen=False
    try:
        message=MotionState(state='FAULT',fault_reason='fixture_lost_posture');message.header.frame_id='base_link'
        end=time.monotonic()+3.
        while not seen and time.monotonic()<end:
            publisher.publish(message);time.sleep(.02)
            try:owner.check()
            except RuntimeError:seen=True
        assert seen
        owner.set_stage('shutdown')
        data=owner.finish(timeout_sec=10.);report=owner.report()
        assert report['joined'] and report['exitcode']==0 and report['error'] is None
        assert report['runtime_fault'] and data['frames']==[]
        assert (tmp_path/'observations.jsonl').stat().st_size>0
        with pytest.raises(RuntimeError):owner.check()
        assert owner.finish(timeout_sec=10.) is data
    finally:
        try:owner.finish(timeout_sec=10.)
        except RuntimeError:pass
        peer.destroy_node();context.try_shutdown()
