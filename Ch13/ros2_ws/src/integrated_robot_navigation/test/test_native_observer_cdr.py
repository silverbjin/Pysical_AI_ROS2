"""Original CDR and prefix ownership; these tests are not physics acceptance."""
import importlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import zlib

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
MAGIC=b'CH13CDR1\n'


def api():
    assert importlib.util.find_spec('native_observer_13_5'), 'native CDR witness reader missing'
    return importlib.import_module('native_observer_13_5')


def record(meta,payload=b''):
    header=json.dumps(meta,separators=(',',':')).encode()
    body=struct.pack('<I',len(header))+header+payload
    return struct.pack('<II',len(body),zlib.crc32(body))+body


def journal(rows):
    return MAGIC+b''.join(record(dict(row,sequence=i+1),payload) for i,(row,payload) in enumerate(rows))


def test_reader_preserves_original_cdr_and_original_receipt():
    raw=b'\x00\x01\x00\x00original_cdr'
    data=journal([(dict(kind='packet',key='contacts',received_ns=10,callback_system_ns=20),raw),
                  (dict(kind='end',records=1),b'')])
    rows=list(api().read_records(io.BytesIO(data)))
    assert rows[0]['payload']==raw and rows[0]['meta']['received_ns']==10
    assert rows[-1]['meta']['records']==1


@pytest.mark.parametrize('change',['crc','truncated','no_footer','sequence','trailing','huge'])
def test_reader_rejects_incomplete_or_changed_recording(change):
    module=api()
    packet=record(dict(kind='packet',sequence=1,key='contacts',received_ns=10),b'cdr')
    footer=record(dict(kind='end',sequence=2,records=1))
    data=MAGIC+packet+footer
    if change=='crc':data=data[:-1]+bytes([data[-1]^1])
    if change=='truncated':data=data[:-2]
    if change=='no_footer':data=MAGIC+packet
    if change=='sequence':data=MAGIC+packet+record(dict(kind='end',sequence=3,records=1))
    if change=='trailing':data+=b'x'
    if change=='huge':data=MAGIC+struct.pack('<II',8*1024*1024+1,0)
    with pytest.raises(ValueError):list(module.read_records(io.BytesIO(data)))


def test_replay_never_uses_a_future_prefix_or_renews_duplicate_receipt(tmp_path):
    from integrated_robot_interfaces.msg import FootContacts
    from rclpy.serialization import serialize_message
    msg=FootContacts();msg.header.frame_id='odom';msg.header.stamp.sec=2
    payload=serialize_message(msg)
    # The first frame precedes receipt entirely. The duplicate is an actual
    # second packet, not permission to replace the first receipt for capture2s.
    rows=[(dict(kind='frame',ros_ns=2_000_000_000,wall_ns=99,stage='stand'),b''),
          (dict(kind='packet',key='contacts',received_ns=100,callback_system_ns=200,
                source_system_ns=180,rmw_received_system_ns=190,gid='00'*24,stage='stand'),payload),
          (dict(kind='packet',key='contacts',received_ns=150,callback_system_ns=250,
                source_system_ns=180,rmw_received_system_ns=240,gid='00'*24,stage='stand'),payload),
          (dict(kind='frame',ros_ns=2_000_000_000,wall_ns=160,stage='stand'),b''),
          (dict(kind='end',records=4),b'')]
    source=tmp_path/'observations.cdr';source.write_bytes(journal(rows))
    result=api().replay_recording(tmp_path,dict(engine='gazebo',records=5))
    exported=[json.loads(line) for line in (tmp_path/'observations.jsonl').read_text().splitlines()]
    contacts=[r['value'] for r in exported if r['kind']=='contacts']
    assert len(contacts)==2 and [v['received_ns'] for v in contacts]==[100,150]
    # SensorInbox's first receipt survives before its first bundle too.
    assert result['selected_prefixes'][-1]['samples']['contacts']['received_ns']==100
    assert not result['frames'], 'incomplete input became complete physical evidence'


def test_replay_rejects_packet_that_was_received_after_frame_cutoff(tmp_path):
    from integrated_robot_interfaces.msg import FootContacts
    from rclpy.serialization import serialize_message
    msg=FootContacts();msg.header.frame_id='odom';msg.header.stamp.sec=1
    rows=[(dict(kind='packet',key='contacts',received_ns=100,callback_system_ns=200,
                source_system_ns=180,rmw_received_system_ns=190,gid='00'*24,stage='stand'),serialize_message(msg)),
          (dict(kind='frame',ros_ns=1,wall_ns=99,stage='stand'),b''),
          (dict(kind='end',records=2),b'')]
    (tmp_path/'observations.cdr').write_bytes(journal(rows))
    with pytest.raises(ValueError,match='cutoff|CDR'):
        api().replay_recording(tmp_path,dict(engine='gazebo',records=3))


def test_native_process_owns_actual_dds_and_normal_stop(tmp_path):
    import os
    import time
    import rclpy
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from integrated_robot_interfaces.msg import FootContacts
    module=api()
    assert hasattr(module,'NativeObserverProcess'), 'native DDS receiver process missing'
    context=Context();rclpy.init(context=context)
    peer=Node('native_cdr_fixture_peer',context=context)
    pub=peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    owner=module.NativeObserverProcess(tmp_path,engine='gazebo')
    try:
        assert owner.identity['pid']!=os.getpid() and owner.identity['uid']==os.getuid()
        owner.set_stage('stand')
        end=time.monotonic()+3.
        while pub.get_subscription_count()!=1 and time.monotonic()<end:time.sleep(.01)
        assert pub.get_subscription_count()==1
        msg=FootContacts();msg.header.frame_id='odom'
        for i in range(30):
            msg.header.stamp.sec=17;msg.header.stamp.nanosec=i*1_000_000
            msg.sequence=i;pub.publish(msg);time.sleep(.01)
        values=owner.finish(timeout_sec=10.)
        report=owner.report()
        assert report['joined'] and report['exitcode']==0 and report['receiver']['closed']
        assert report['journal']['submitted']==report['journal']['written']
        assert report['ipc_requests']==2
        rows=[json.loads(line) for line in (tmp_path/'observations.jsonl').read_text().splitlines()]
        contacts=[r['value'] for r in rows if r['kind']=='contacts']
        assert len(contacts)>=20 and contacts[-1]['stamp_ns']==17_029_000_000
        assert contacts[-1]['received_ns']>0 and not values['frames']
        assert not values['errors'] and report['recording']['raw_sha256']
    finally:
        owner.finish(timeout_sec=10.)
        peer.destroy_node();context.try_shutdown()


def test_split_probe_can_explicitly_select_native_cdr_without_changing_default(tmp_path):
    import inspect
    import rclpy
    from rclpy.context import Context
    from split_observer_13_5 import SplitNavigationProbe
    assert 'observer_backend' in inspect.signature(SplitNavigationProbe).parameters, 'explicit observer backend missing'
    assert inspect.signature(SplitNavigationProbe).parameters['observer_backend'].default=='python'
    context=Context();rclpy.init(context=context)
    probe=SplitNavigationProbe(tmp_path,engine='gazebo',observer_backend='native_cdr',context=context)
    try:
        assert probe.observer.identity['backend']=='native_cdr'
        probe.set_stage('stand')
        probe.restore_history(receiver_joined=True)
        assert probe.observer.report()['joined'] and probe.full_restored
    finally:
        probe.observer.finish(timeout_sec=10.)
        probe.close_log();probe.destroy_node();context.try_shutdown()


def test_native_parent_connection_loss_drains_and_remains_failed(tmp_path):
    owner=api().NativeObserverProcess(tmp_path,engine='gazebo')
    owner.process.stdin.close()
    try:
        with pytest.raises(RuntimeError):owner.finish(timeout_sec=10.)
        report=owner.report()
        assert report['joined'] and report['exitcode']!=0 and report['error']
        assert report['journal']['joined'] and report['receiver']['closed']
        native=json.loads((tmp_path/'observer_native_report.json').read_text())
        assert native['failure'] and native['journal']['submitted']==native['journal']['written']
    finally:
        # Even the expected RED must reap its own failed child without a signal.
        owner.process.wait(timeout=10.)
        owner.process.stdout.close();owner.stderr.close()


def complete_packets(stamp=2_000_000_000,receipt=100_000_000_000):
    from geometry_msgs.msg import PoseStamped,Point
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import JointState,Imu,LaserScan
    from integrated_robot_interfaces.msg import MotionState,FootContacts
    from rclpy.serialization import serialize_message
    messages=dict(joints=JointState(name=['joint'],position=[.1],velocity=[0.]),imu=Imu(),
        contacts=FootContacts(names=['fr_foot','fl_foot','rr_foot','rl_foot'],
            points=[Point() for _ in range(4)],normal_forces=[30.]*4,touching=[True]*4),
        body=Odometry(child_frame_id='base_footprint'),
        scan=LaserScan(range_min=.05,range_max=10.,ranges=[10.]*360),
        carry=MotionState(ready=True),native_com=PoseStamped())
    messages['body'].pose.pose.orientation.w=1.
    messages['body'].pose.pose.position.z=.46
    rows=[]
    for key,message in messages.items():
        message.header.stamp.sec=stamp//1_000_000_000;message.header.stamp.nanosec=stamp%1_000_000_000
        message.header.frame_id={'body':'odom','contacts':'odom','scan':'lidar_link','native_com':'odom'}.get(key,'base_link')
        rows.append((dict(kind='packet',key=key,received_ns=receipt,callback_system_ns=receipt+1000,
            source_system_ns=receipt+900,rmw_received_system_ns=receipt+950,gid='01'*24,stage='stand'),serialize_message(message)))
    return rows


def test_all_original_stale_frames_survive_replay_and_fail_same_age_contract(tmp_path):
    from integrated_robot_navigation.samples import Sample,SensorBundle,validate_bundle
    rows=complete_packets()
    rows.extend([(dict(kind='frame',ros_ns=2_000_000_000,wall_ns=100_000_000_000,stage='stand'),b''),
        (dict(kind='frame',ros_ns=2_201_000_000,wall_ns=100_201_000_000,stage='stand'),b'')])
    rows.append((dict(kind='end',records=len(rows)),b''))
    (tmp_path/'observations.cdr').write_bytes(journal(rows))
    values=api().replay_recording(tmp_path,dict(engine='gazebo',records=len(rows)))
    assert len(values['frames'])==2, 'stale frame was silently excluded'
    for frame,valid in zip(values['frames'],[True,False]):
        samples=SensorBundle(**{key:Sample(**frame['samples'][key]) for key in
            ('joints','imu','contacts','body','scan','carry')})
        ok,reason=validate_bundle(samples,frame['ros_ns'],frame['wall_ns'],0)
        assert ok is valid
        if not valid:assert reason=='joints:ros_age'
        assert frame['samples']['joints']['received_ns']==100_000_000_000


def test_future_capture_stays_pending_until_original_ros_time(tmp_path):
    rows=complete_packets(stamp=2_000_000_001)
    rows.extend([(dict(kind='frame',ros_ns=2_000_000_000,wall_ns=100_000_000_000,stage='stand'),b''),
        (dict(kind='frame',ros_ns=2_000_000_001,wall_ns=100_000_000_001,stage='stand'),b'')])
    rows.append((dict(kind='end',records=len(rows)),b''))
    (tmp_path/'observations.cdr').write_bytes(journal(rows))
    values=api().replay_recording(tmp_path,dict(engine='gazebo',records=len(rows)))
    assert len(values['frames'])==1 and values['frames'][0]['ros_ns']==2_000_000_001
    assert values['frames'][0]['samples']['joints']['stamp_ns']==2_000_000_001
    assert values['selected_prefixes'][0]['samples']['joints'] is None


def test_application_wire_trace_is_separate_from_client_receipt_and_grants_no_credit(tmp_path):
    from sensor_msgs.msg import JointState
    from rclpy.serialization import serialize_message
    message=JointState(name=['a','b'],position=[.1,.2])
    message.header.frame_id='mujoco/pre_step';message.header.stamp.sec=2
    rows=[(dict(kind='packet',key='applied_reference',received_ns=100,callback_system_ns=200,
        source_system_ns=180,rmw_received_system_ns=190,gid='01'*24,stage='forward'),serialize_message(message)),
        (dict(kind='end',records=1),b'')]
    (tmp_path/'observations.cdr').write_bytes(journal(rows))
    result=api().replay_recording(tmp_path,dict(engine='gazebo',records=2))
    values=[json.loads(line) for line in (tmp_path/'observations.jsonl').read_text().splitlines()]
    ack=next(row['value'] for row in values if row['kind']=='applied_reference')
    assert ack['stamp_ns']==2_000_000_000 and ack['received_ns']==100
    assert ack['data']==dict(name=['a','b'],position=[.1,.2])
    assert ack['scope']=='independent_observer_receipt_not_controller_receipt_or_credit'
    assert not result['frames']


def test_native_dds_complete_prefix_clock_and_original_messages(tmp_path):
    import time
    import rclpy
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.serialization import deserialize_message
    from rosgraph_msgs.msg import Clock
    from integrated_robot_navigation.samples import Sample,SensorBundle,validate_bundle
    module=api();context=Context();rclpy.init(context=context)
    peer=Node('native_complete_fixture',context=context)
    topics=dict(joints='/joint_states',imu='/navigation/imu',contacts='/navigation/foot_contacts',
        body='/odom',scan='/scan',carry='/navigation/carry_state',native_com='/navigation/native_com')
    types=module._message_types()
    publishers={key:peer.create_publisher(types[key],topic,10) for key,topic in topics.items()}
    clock=peer.create_publisher(Clock,'/clock',10)
    owner=module.NativeObserverProcess(tmp_path,engine='gazebo')
    try:
        owner.set_stage('stand');end=time.monotonic()+3.
        while not all(pub.get_subscription_count() for pub in [clock,*publishers.values()]) and time.monotonic()<end:
            time.sleep(.01)
        assert all(pub.get_subscription_count() for pub in [clock,*publishers.values()])
        for i in range(60):
            stamp=2_000_000_000+i*20_000_000
            clock_msg=Clock();clock_msg.clock.sec=stamp//1_000_000_000;clock_msg.clock.nanosec=stamp%1_000_000_000
            clock.publish(clock_msg)
            for meta,payload in complete_packets(stamp=stamp):
                publishers[meta['key']].publish(deserialize_message(payload,types[meta['key']]))
            time.sleep(.02)
        values=owner.finish(timeout_sec=10.)
        assert len(values['frames'])>=10 and not values['errors']
        for frame in values['frames']:
            samples=SensorBundle(**{key:Sample(**frame['samples'][key]) for key in
                ('joints','imu','contacts','body','scan','carry')})
            assert validate_bundle(samples,frame['ros_ns'],frame['wall_ns'],0)==(True,'')
            assert frame['samples']['body']['data']['position']==(0.,0.,.46)
    finally:
        owner.finish(timeout_sec=10.);peer.destroy_node();context.try_shutdown()


def test_native_wire_gid_ack_and_fault_remain_distinct_from_normal_exit(tmp_path):
    import time
    import rclpy
    from rclpy.context import Context
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from geometry_msgs.msg import TransformStamped
    from tf2_msgs.msg import TFMessage
    from integrated_robot_interfaces.msg import MotionState
    context=Context();rclpy.init(context=context);peer=Node('native_wire_fixture',context=context)
    ack=peer.create_publisher(JointState,'/navigation/applied_reference',1)
    tf=peer.create_publisher(TFMessage,'/tf',10)
    motion=peer.create_publisher(MotionState,'/navigation/crawl_state',10)
    owner=api().NativeObserverProcess(tmp_path,engine='mujoco')
    try:
        owner.set_stage('stand');end=time.monotonic()+3.
        while not all(pub.get_subscription_count() for pub in (ack,tf,motion)) and time.monotonic()<end:time.sleep(.01)
        assert all(pub.get_subscription_count() for pub in (ack,tf,motion))
        message=JointState(name=['a'],position=[.1]);message.header.frame_id='mujoco/pre_step';message.header.stamp.sec=17
        transform=TransformStamped(child_frame_id='nav_base');transform.header.frame_id='odom';transform.header.stamp.sec=17
        for i in range(5):ack.publish(message);tf.publish(TFMessage(transforms=[transform]));time.sleep(.02)
        references=owner.transforms();assert references and references[-1]['stamp_ns']==17_000_000_000
        gids={bytes(value.endpoint_gid).hex() for value in peer.get_publishers_info_by_topic('/tf')}
        assert references[-1]['gid'] in gids
        message=MotionState(state='FAULT',fault_reason='fixture_fault');motion.publish(message)
        end=time.monotonic()+2.
        while not owner.runtime_fault and time.monotonic()<end:
            try:owner.check()
            except RuntimeError:
                if not owner.runtime_fault:raise
            time.sleep(.01)
        assert owner.runtime_fault and 'fixture_fault' in owner.runtime_fault['reason']
        before=owner.ipc_requests
        with pytest.raises(RuntimeError,match='runtime fault'):owner.set_stage('forward')
        assert owner.ipc_requests==before
        owner.set_stage('shutdown');values=owner.finish(timeout_sec=10.)
        assert owner.report()['exitcode']==0 and owner.report()['runtime_fault']
        rows=[json.loads(line) for line in (tmp_path/'observations.jsonl').read_text().splitlines()]
        acks=[row['value'] for row in rows if row['kind']=='applied_reference']
        assert acks and acks[-1]['stamp_ns']==17_000_000_000
        assert not values['frames']
    finally:
        owner.finish(timeout_sec=10.);peer.destroy_node();context.try_shutdown()


def test_clean_stderr_log_carries_actual_lifecycle_and_passes_existing_artifact_contract(tmp_path):
    from verify_vision_13_4 import EvidenceRun
    owner=api().NativeObserverProcess(tmp_path,engine='gazebo')
    try:
        owner.finish(timeout_sec=10.);report=owner.report()
        with EvidenceRun(tmp_path,{'native_drain'}) as evidence:
            evidence.artifact(tmp_path/'native_observer.stderr.log')
            evidence.finish(dict(native_drain=report['joined'] and report['exitcode']==0
                and report['receiver']['closed'] and report['journal']['joined']))
        assert evidence.result['status']=='PASS'
        lines=(tmp_path/'native_observer.stderr.log').read_text().splitlines()
        begin,end=json.loads(lines[0]),json.loads(lines[-1])
        assert begin['event']=='stderr_capture_open' and begin['executable_sha256']==owner.identity['executable_sha256']
        assert end['event']=='stderr_capture_closed' and end['pid']==owner.identity['pid']
        assert end['returncode']==0 and end['native_stderr_bytes']==0
    finally:owner.finish(timeout_sec=10.)
