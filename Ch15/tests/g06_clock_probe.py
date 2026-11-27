"""T15 supplemental: actual ROS clock, DDS delete after rewind, physical source label.
No simulator or robot is started. Physical-shaped observation is explicitly a fixture.
"""
import json,os,signal,subprocess,sys,time
from copy import deepcopy
from pathlib import Path
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_prefix
from rosgraph_msgs.msg import Clock
from ch15_interfaces.msg import MissionStatus,TargetObservation
from visualization_msgs.msg import Marker

out=Path(sys.argv[1]);results={};captures=[];proc=None
rclpy.init();n=Node('g06_clock_fixture')
cp=n.create_publisher(Clock,'/clock',10)
tp=n.create_publisher(TargetObservation,'/ch15/target_observation',10)
sp=n.create_publisher(MissionStatus,'/ch15/mission_state',10)
def capture(m):
    captures.append(dict(ns=m.ns,id=m.id,action=m.action,frame=m.header.frame_id,sec=m.header.stamp.sec,nanosec=m.header.stamp.nanosec,x=m.pose.position.x,w=m.pose.orientation.w,lifetime=m.lifetime.sec,text=m.text))
n.create_subscription(Marker,'/ch15/visualization/target',capture,100)
n.create_subscription(Marker,'/ch15/visualization/status',capture,100)
def wait(pred,timeout=4):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        rclpy.spin_once(n,timeout_sec=.01)
        if pred():return
    raise AssertionError('DDS predicate deadline')
def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.01)
def clock(sec):
    c=Clock();c.clock.sec=sec;cp.publish(c);spin(.075)
def launch(mode):
    global proc
    exe=Path(get_package_prefix('ch15_visualization'))/'lib/ch15_visualization/mission_marker_node'
    proc=subprocess.Popen([str(exe),'--ros-args','-p','mode:='+mode,'-p','use_sim_time:=true'],start_new_session=True)
    wait(lambda:cp.get_subscription_count()==1 and tp.get_subscription_count()==1 and n.count_publishers('/ch15/visualization/target')==1 and n.count_publishers('/ch15/visualization/status')==1,8)
def stop():
    global proc
    if proc is None:return
    os.killpg(proc.pid,signal.SIGINT)
    try:rc=proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise
    proc=None
    assert rc==0,rc
    wait(lambda:cp.get_subscription_count()==0 and n.count_publishers('/ch15/visualization/target')==0,5)
def target(sec):
    m=TargetObservation();m.mission_id='cube_lab';m.epoch=0;m.source='RGBD_COLOR';m.pose_kind='POSITION_ONLY';m.object_class='red_cube';m.valid=True
    m.header.frame_id='map';m.header.stamp.sec=sec;m.target_pose.header=deepcopy(m.header)
    m.target_pose.pose.position.x=.45;m.target_pose.pose.orientation.w=1.
    return m
def state(sec):
    m=MissionStatus();m.mission_id='mock_record';m.epoch=1;m.profile='mock';m.source='MOCK';m.state='COMPLETED';m.header.stamp.sec=sec
    return m
def actions(start,ns,action):
    return [m for m in captures[start:] if m['ns']==ns and m['action']==action]
def graph_check():
    pubs={name for name,_ in n.get_topic_names_and_types() if any(p.node_name=='ch15_mission_marker' for p in n.get_publishers_info_by_topic(name))}
    assert pubs-{'/rosout','/parameter_events'}=={'/ch15/visualization/target','/ch15/visualization/status'}
    services=n.get_service_names_and_types_by_node('ch15_mission_marker','/')
    assert all(name.startswith('/ch15_mission_marker/') for name,_ in services)
    return sorted(pubs)
try:
    launch('physical');clock(10)
    start=len(captures);tp.publish(target(10))
    wait(lambda:{m['id'] for m in actions(start,'ch15_target',Marker.ADD)}=={0,2},.2)
    a=actions(start,'ch15_target',Marker.ADD)
    assert all(m['frame']=='map' and m['sec']==10 and m['nanosec']==0 and m['w']==1. and m['lifetime']==1 and m['x']==.45 for m in a)
    assert any('PHYSICAL | source=RGBD_COLOR | POSITION_ONLY' in m['text'] for m in a)
    results['physical_fixture']='PASS';results['physical_graph']=graph_check()
    start=len(captures);clock(9)
    wait(lambda:{m['id'] for m in actions(start,'ch15_target',Marker.DELETE)}=={0,2})
    clock(11);tp.publish(target(11));spin(.18)
    assert not actions(start,'ch15_target',Marker.ADD)
    results['target_rewind_delete_and_no_ghost']='PASS';stop()
    launch('replay');clock(20);start=len(captures);sp.publish(state(20))
    wait(lambda:any('REPLAY | source=MOCK | profile=mock | COMPLETED' in m['text'] for m in actions(start,'ch15_status',Marker.ADD)),.2)
    results['replay_graph']=graph_check()
    start=len(captures);clock(19)
    wait(lambda:{m['id'] for m in actions(start,'ch15_status',Marker.DELETE)}=={1})
    clock(21);sp.publish(state(21));tp.publish(target(21));spin(.18)
    assert not actions(start,'ch15_status',Marker.ADD) and not actions(start,'ch15_target',Marker.ADD)
    results['replay_rewind_delete_and_no_ghost']='PASS'
    stop();results['clean_exit']=True;results['result']='PASS'
except BaseException as e:
    results['result']='FAIL';results['error']=repr(e);raise
finally:
    try:
        if proc is not None:stop()
    finally:
        n.destroy_node();rclpy.try_shutdown()
        out.write_text(json.dumps(dict(results=results,captures=captures),indent=2)+'\n')
