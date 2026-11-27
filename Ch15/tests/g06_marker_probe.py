"""Actual ROS DDS fixture, independent producer/consumer versus installed node."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
from copy import deepcopy
import rclpy
from rclpy.node import Node
from ch15_interfaces.msg import MissionStatus,TargetObservation,SafetyState
from visualization_msgs.msg import Marker
from ament_index_python.packages import get_package_prefix

out=Path(sys.argv[1]);results={};captures=[];proc=None
rclpy.init();n=Node('g06_fixture')
sp=n.create_publisher(MissionStatus,'/ch15/mission_state',10)
tp=n.create_publisher(TargetObservation,'/ch15/target_observation',10)
safe=n.create_publisher(SafetyState,'/ch15/safety_state',10)
def capture(m):
    captures.append(dict(ns=m.ns,id=m.id,action=m.action,frame=m.header.frame_id,sec=m.header.stamp.sec,nanosec=m.header.stamp.nanosec,x=m.pose.position.x,y=m.pose.position.y,z=m.pose.position.z,w=m.pose.orientation.w,lifetime=m.lifetime.sec,text=m.text))
n.create_subscription(Marker,'/ch15/visualization/target',capture,100)
n.create_subscription(Marker,'/ch15/visualization/status',capture,100)
def wait(pred,timeout=3):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        rclpy.spin_once(n,timeout_sec=.02)
        if pred():return
    raise AssertionError('DDS predicate deadline')
def launch(mode):
    global proc
    proc=subprocess.Popen([str(Path(get_package_prefix('ch15_visualization'))/'lib/ch15_visualization/mission_marker_node'),'--ros-args','-p','mode:='+mode],start_new_session=True)
    wait(lambda:sp.get_subscription_count()==1 and tp.get_subscription_count()==1 and n.count_publishers('/ch15/visualization/target')==1 and n.count_publishers('/ch15/visualization/status')==1,8)
def stop():
    global proc
    if proc is not None:
        os.killpg(proc.pid,signal.SIGINT)
        try:rc=proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise
        proc=None
        assert rc==0,rc
        wait(lambda:sp.get_subscription_count()==0 and n.count_publishers('/ch15/visualization/target')==0,5)
def status(epoch=1):
    m=MissionStatus();m.mission_id='fixture';m.epoch=epoch;m.profile='mock';m.source='MOCK';m.state='SEARCHING';m.header.stamp=n.get_clock().now().to_msg()
    s=SafetyState();s.epoch=epoch;s.owner='MOCK:ch15_command_arbiter';s.blocked=True;s.header.stamp=m.header.stamp
    safe.publish(s);sp.publish(m)
def target(epoch=1,x=.5):
    m=TargetObservation();m.mission_id='fixture';m.epoch=epoch;m.source='MOCK';m.pose_kind='GRASP_POSE';m.object_class='red_cube';m.valid=True
    m.header.frame_id='map';m.header.stamp=n.get_clock().now().to_msg();m.target_pose.header=deepcopy(m.header)
    m.target_pose.pose.position.x=x;m.target_pose.pose.orientation.w=1.
    return m
def adds(start):
    return [a for a in captures[start:] if a['ns']=='ch15_target' and a['action']==Marker.ADD and a['id']==0]
def deletes(start):
    return {a['id'] for a in captures[start:] if a['ns']=='ch15_target' and a['action']==Marker.DELETE}
def send_good(i,epoch=1):
    start=len(captures);status(epoch)
    # Ensure new status is consumed before the target (DDS topics have independent ordering).
    wait(lambda:any(a['ns']=='ch15_status' and a['action']==Marker.ADD and ('epoch='+str(epoch)) in a['text'] for a in captures[start:]))
    m=target(epoch,i/100.);start=len(captures);tp.publish(m)
    wait(lambda:len(adds(start))==1 and any(a['ns']=='ch15_target' and a['id']==2 and a['action']==Marker.ADD for a in captures[start:]))
    a=adds(start)[0]
    assert (a['frame'],a['sec'],a['nanosec'],a['x'],a['w'],a['lifetime'])==('map',m.header.stamp.sec,m.header.stamp.nanosec,i/100.,1.,1)
    return m
try:
    launch('mock')
    for i in range(10):send_good(i)
    results['valid_add']=10
    for name in ('nan','wrong_frame','stale','epoch'):
        send_good(50)
        m=target()
        if name=='nan':m.target_pose.pose.position.x=float('nan')
        if name=='wrong_frame':m.header.frame_id=m.target_pose.header.frame_id='bad'
        if name=='stale':m.header.stamp.sec-=1;m.target_pose.header=deepcopy(m.header)
        if name=='epoch':m.epoch=7
        start=len(captures);tp.publish(m);wait(lambda:deletes(start)=={0,2});assert not adds(start);results[name]='PASS'
    send_good(51);start=len(captures);status(2);wait(lambda:deletes(start)=={0,2})
    results['epoch_delete']='PASS'
    send_good(52,2);start=len(captures);wait(lambda:deletes(start)=={0,2});results['receipt_expiry']='PASS'
    graph={}
    for name,_ in n.get_topic_names_and_types():
        pubs=n.get_publishers_info_by_topic(name)
        if any(p.node_name=='ch15_mission_marker' for p in pubs):graph[name]=[p.node_name for p in pubs]
    assert set(graph)-{'/rosout','/parameter_events'}=={'/ch15/visualization/target','/ch15/visualization/status'},graph
    results['publisher_graph']=graph
    stop();launch('replay')
    start=len(captures);status()
    wait(lambda:any('REPLAY | source=MOCK' in a['text'] for a in captures[start:]))
    tp.publish(target());end=time.monotonic()+.4
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.02)
    assert not adds(start);results['replay_no_ghost']='PASS'
    stop();results['clean_exit']=True;results['result']='PASS'
except BaseException as e:
    results['result']='FAIL';results['error']=repr(e);raise
finally:
    try:
        if proc is not None:stop()
    finally:
        n.destroy_node();rclpy.try_shutdown()
        out.write_text(json.dumps({'results':results,'captures':captures},indent=2)+'\n')
