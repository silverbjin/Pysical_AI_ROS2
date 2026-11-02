"""Actual DDS pair with intentionally delayed ROS Clock; no physics engine."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from std_srvs.srv import Trigger
from integrated_robot_interfaces.msg import FootContacts
from integrated_robot_navigation.scene import materialize_scene,load_scene
from test_gazebo_contacts import pair

def test_actual_adapter_preserves_pair_until_original_clock_catches_up(tmp_path):
    scene=tmp_path/'scene';materialize_scene('gazebo','g1',scene,g1_reference_ramp=True,g1_contact_allowance=True)
    record=load_scene('gazebo',str(scene));source=Path(__file__).resolve().parents[1]
    code='import sys;sys.path.insert(0,'+repr(str(source))+');from integrated_robot_navigation.gazebo_contacts import main;main(args='+repr(['--ros-args','-p','scene_dir:='+str(scene),'-p','use_sim_time:=true'])+');print("NORMAL_DDS_PAIR_EXIT",flush=True)'
    context=Context();rclpy.init(context=context);peer=Node('pair_clock_peer',context=context);executor=SingleThreadedExecutor(context=context);executor.add_node(peer)
    contacts,feet=pair();contacts.contacts[0].collision1.name=next(iter(record['foot_collision_map']))
    pubs=[peer.create_publisher(type(contacts),'/navigation/native_contacts',qos_profile_sensor_data),peer.create_publisher(type(feet),'/navigation/native_feet',qos_profile_sensor_data),peer.create_publisher(Clock,'/clock',qos_profile_sensor_data)]
    output=[];peer.create_subscription(FootContacts,'/navigation/foot_contacts',output.append,qos_profile_sensor_data)
    client=peer.create_client(Trigger,'/gazebo_contact_adapter/report');process=None;trace={}
    def pump(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:executor.spin_once(timeout_sec=.01)
    def snapshot():
        future=client.call_async(Trigger.Request());end=time.monotonic()+2.
        while not future.done() and time.monotonic()<end:executor.spin_once(timeout_sec=.01)
        assert future.done();return json.loads(future.result().message)
    try:
        with (tmp_path/'stdout.log').open('w') as stdout,(tmp_path/'stderr.log').open('w') as stderr:
            process=subprocess.Popen([sys.executable,'-c',code],stdout=stdout,stderr=stderr,start_new_session=True)
            assert client.wait_for_service(timeout_sec=8.)
            end=time.monotonic()+3.
            while not all(p.get_subscription_count() for p in pubs) and time.monotonic()<end:pump(.02)
            assert all(p.get_subscription_count() for p in pubs)
            clock=Clock();clock.clock.sec=3;clock.clock.nanosec=990_000_000;pubs[2].publish(clock)
            end=time.monotonic()+2.
            while time.monotonic()<end:
                if snapshot()['observed_clock_ns']==3_990_000_000:break
                pump(.01)
            assert snapshot()['observed_clock_ns']==3_990_000_000
            pump(.05);pubs[0].publish(contacts);pubs[1].publish(feet)
            end=time.monotonic()+2.
            while time.monotonic()<end:
                state=snapshot()
                if state['counts']['contacts']==state['counts']['feet']==1:break
                pump(.01)
            trace['before_clock']=snapshot();assert not output
            clock.clock.sec=4;clock.clock.nanosec=10_000_000;pubs[2].publish(clock)
            pump(.08);trace['after_clock']=snapshot();trace['outputs']=len(output)
            assert len(output)==1,trace
            assert output[0].header.stamp==contacts.header.stamp and output[0].epoch==0
            assert trace['after_clock']['expired']=={'contacts':0,'feet':0}
    finally:
        if process is not None:
            process.send_signal(signal.SIGINT);process.wait(timeout=6.)
            trace['returncode']=process.returncode;assert process.returncode==0
        executor.remove_node(peer);peer.destroy_node();executor.shutdown();context.try_shutdown()
        destination=Path(os.environ.get('CH13_PAIR_TRACE_DIR',str(tmp_path)));destination.mkdir(parents=True,exist_ok=True)
        (destination/'dds-pair-trace.json').write_text(json.dumps(trace,indent=2))
