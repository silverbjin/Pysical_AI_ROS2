"""Actual multiprocess DDS witness; no physical robot. Bounded process ownership."""
import json,os,pathlib,signal,subprocess,sys,time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String
from std_srvs.srv import Trigger
from ch15_interfaces.action import PickObject,PlaceObject
from ch15_interfaces.srv import SwitchGait
from ch15_interfaces.msg import ReadyState,SafetyState
from ch15_adapters.qos_profiles import profile,state_qos

out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
rows=[];children=[]
def launch(pkg,exe,*args):
    path=pathlib.Path(os.environ['G02_INSTALL'])/pkg/'lib'/pkg/exe
    stream=(out/(exe+'.log')).open('w')
    child=subprocess.Popen([str(path),*args],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    children.append((exe,child,stream))
def record(label,**data):
    row=dict(label=label,**data);rows.append(row);print(json.dumps(row),flush=True)
rclpy.init();node=Node('ch15_g02_probe')
ready=[];safety=[];motion=[];gait=[];witness=[];be=[];rel=[];late=[];life=[False]
subs=[]
def sub(typ,name,buffer,q):
    subs.append(node.create_subscription(typ,name,lambda m:buffer.append(m),q))
sub(ReadyState,'/ch15/ready',ready,profile())
sub(SafetyState,'/ch15/safety_state',safety,state_qos)
sub(Twist,'/cmd_vel',motion,profile())
sub(String,'/ch15/gait_state',gait,profile(transient=True))
sub(String,'/ch15/mock_witness',witness,profile(10))
sub(String,'/ch15/qos_demo/sensor',be,profile(10,reliable=False))
sub(String,'/ch15/qos_demo/sensor',rel,profile(10))
def get_state(req,res):
    res.current_state.id=3 if life[0] else 2
    res.current_state.label='active' if life[0] else 'inactive'
    return res
service=node.create_service(GetState,'/g02_lifecycle_fixture/get_state',get_state)
def until(pred,seconds=5):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        for name,p,_ in children:
            assert p.poll() is None,(name,p.returncode)
        rclpy.spin_once(node,timeout_sec=.02)
        if pred():return
    raise AssertionError('deadline: '+str(rows[-1] if rows else 'startup'))
def spin_for(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.02)
def call(client,req):
    until(client.service_is_ready);f=client.call_async(req);until(f.done);return f.result()
def latest_ready():return bool(ready and ready[-1].ready)
def goal(client,req,accept=True,cancel=False):
    until(client.server_is_ready)
    feedback=[]
    f=client.send_goal_async(req,feedback_callback=lambda m:feedback.append(m.feedback))
    until(f.done);h=f.result();assert h.accepted==accept
    if not accept:record('rejected');return
    rf=h.get_result_async()
    if cancel:
        cf=h.cancel_goal_async();until(cf.done);assert cf.result().goals_canceling
    until(rf.done,8);res=rf.result()
    expected=GoalStatus.STATUS_CANCELED if cancel else GoalStatus.STATUS_SUCCEEDED
    assert res.status==expected,(res.status,expected)
    if not cancel:assert feedback,'no feedback'
    if hasattr(res.result,'success'):assert res.result.success==(not cancel)
    if hasattr(res.result,'error_code') and not cancel:assert res.result.error_code==0
    record('action_terminal',uuid=bytes(h.goal_id.uuid).hex(),status=res.status,feedback=len(feedback),action=type(req).__name__)
def pose(p):
    p.header.frame_id='map';p.header.stamp=node.get_clock().now().to_msg();p.pose.position.x=1.;p.pose.orientation.w=1.
error=None;exits=[]
try:
    launch('ch15_safety','command_arbiter')
    launch('ch15_safety','readiness_monitor','--ros-args','-p','required_lifecycle_node:=/g02_lifecycle_fixture')
    until(lambda:ready and {'server','sensor','tf','heartbeat','lifecycle','owner'}.issubset(ready[-1].missing))
    until(lambda:motion and safety and safety[-1].blocked)
    assert all(m.linear.x==0. and m.angular.z==0. for m in motion)
    record('startup_blocked',missing=list(ready[-1].missing),zero_samples=len(motion))
    launch('ch15_adapters','mock_servers')
    launch('ch15_safety','sensor_watchdog')
    until(lambda:ready and list(ready[-1].missing)==['lifecycle'],10)
    assert not latest_ready()
    record('lifecycle_inactive_blocked')
    life[0]=True;until(latest_ready,10);record('ready_after_active')
    # Ownership conflict is graph-only: never publish a second command.
    duplicate=node.create_publisher(Twist,'/cmd_vel',profile())
    until(lambda:ready and 'owner' in ready[-1].missing and not ready[-1].ready)
    until(lambda:safety and safety[-1].blocked);record('duplicate_owner_blocked')
    node.destroy_publisher(duplicate);until(latest_ready,10)
    nav=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    pick=ActionClient(node,PickObject,'/pick_object')
    place=ActionClient(node,PlaceObject,'/place_object')
    g=NavigateToPose.Goal();pose(g.pose)
    bad=NavigateToPose.Goal();goal(nav,bad,False)
    goal(nav,g);until(lambda:any(m.linear.x>0 for m in motion))
    client=node.create_client(SwitchGait,'/switch_gait')
    for name in ['crawl','trot','stand']:
        res=call(client,SwitchGait.Request(gait_type=name));assert res.success
        until(lambda:gait and gait[-1].data==name);record('gait_observed',gait=name)
    assert not call(client,SwitchGait.Request(gait_type='invalid')).success;record('invalid_gait_rejected')
    p=PickObject.Goal();p.object_class='red_cube';pose(p.target_pose);p.timeout_sec=0.;goal(pick,p,False)
    p.timeout_sec=5.;goal(pick,p)
    q=PlaceObject.Goal();pose(q.target_pose);q.timeout_sec=0.;goal(place,q,False)
    q.timeout_sec=5.;goal(place,q)
    until(lambda:len(witness)>=3)
    assert [m.data for m in witness][:3]==['MOCK:nav:logical_transition','MOCK:pick:logical_transition','MOCK:place:logical_transition']
    record('mock_witness',values=[m.data for m in witness])
    reset=node.create_client(Trigger,'/ch15/reset_safety');assert not call(reset,Trigger.Request()).success;record('reset_blocked_without_terminal_idle_contract')
    launch('ch15_adapters','qos_demo')
    start=node.create_client(Trigger,'/ch15/qos_demo/start')
    until(lambda:start.service_is_ready() and node.count_publishers('/ch15/qos_demo/sensor')==1)
    spin_for(.5)
    endpoints=node.get_publishers_info_by_topic('/ch15/qos_demo/sensor')
    assert len(endpoints)==1 and endpoints[0].qos_profile.reliability.name=='BEST_EFFORT'
    assert call(start,Trigger.Request()).success
    until(lambda:len(be)>=10,5);spin_for(.3)
    assert [m.data for m in be]==[str(i) for i in range(1,11)] and not rel
    sub(String,'/ch15/mission_state_demo',late,state_qos)
    until(lambda:any(m.data=='S10' for m in late));record('qos',be_count=len(be),reliable_count=len(rel),late_last='S10')
except BaseException as exc:
    error=repr(exc);record('FAIL',error=error)
finally:
    for name,p,stream in reversed(children):
        if p.poll() is None:p.send_signal(signal.SIGINT)
        try:rc=p.wait(timeout=6);forced=False
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=3);forced=True
        stream.close();exits.append(dict(name=name,exit=rc,forced=forced))
    node.destroy_node();rclpy.try_shutdown()
    clean=all(x['exit']==0 and not x['forced'] for x in exits)
    result=dict(source='MOCK',full_mission_success=False,result='PASS' if error is None and clean else 'FAIL',error=error,events=rows,processes=exits)
    (out/'dds-result.json').write_text(json.dumps(result,indent=2)+'\n')
sys.exit(0 if result['result']=='PASS' else 1)
