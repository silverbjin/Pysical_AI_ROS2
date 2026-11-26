"""Two targeted mission boundaries, NOT a normal full mission repetition."""
import json,os,pathlib,signal,subprocess,sys,time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from geometry_msgs.msg import Twist
from ch15_interfaces.msg import MissionStatus,MissionEvent,ReadyState,TargetObservation
from ch15_adapters.qos_profiles import profile,state_qos
mode=sys.argv[1];assert mode in ('cancel','invalid_target')
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
children=[];rows=[];status=[];events=[];ready=[];motion=[]
def launch(pkg,exe,*args):
    p=pathlib.Path(os.environ['G03_INSTALL'])/pkg/'lib'/pkg/exe
    stream=(out/(exe+'.log')).open('w');child=subprocess.Popen([str(p),*args],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);children.append((exe,child,stream))
def record(label,**kw):
    row=dict(label=label,**kw);rows.append(row);print(json.dumps(row),flush=True)
rclpy.init();n=Node('g03_fault_probe')
subs=[n.create_subscription(MissionStatus,'/ch15/mission_state',status.append,state_qos),n.create_subscription(MissionEvent,'/ch15/mission_event',events.append,profile(100)),n.create_subscription(ReadyState,'/ch15/ready',ready.append,profile()),n.create_subscription(Twist,'/cmd_vel',lambda m:motion.append((time.monotonic(),m)),profile())]
start=n.create_client(Trigger,'/ch15/start_mission');cancel=n.create_client(Trigger,'/ch15/cancel_mission');reset=n.create_client(Trigger,'/ch15/reset_safety')
target=None
def until(pred,seconds=10.):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        for name,p,_ in children:assert p.poll() is None,(name,p.returncode)
        rclpy.spin_once(n,timeout_sec=.02)
        if pred():return
    raise AssertionError('deadline '+str(rows[-1] if rows else 'startup'))
def call(c):
    until(c.service_is_ready);f=c.call_async(Trigger.Request());until(f.done);return f.result()
def zero(m):
    return all(abs(x)<=1e-9 for x in (m.linear.x,m.linear.y,m.linear.z,m.angular.x,m.angular.y,m.angular.z))
def invalid():
    if not status or status[-1].state!='SEARCHING':return
    s=status[-1];m=TargetObservation();m.header.frame_id='map';m.header.stamp=n.get_clock().now().to_msg();m.mission_id=s.mission_id;m.epoch=s.epoch+1;m.source='MOCK';m.object_class='red_cube';m.valid=True;m.pose_kind='GRASP_POSE';m.target_pose.header=m.header;m.target_pose.pose.position.x=1.;m.target_pose.pose.position.z=.225;m.target_pose.pose.orientation.w=1.;target.publish(m)
err=None;exits=[]
try:
    launch('ch15_safety','command_arbiter','--ros-args','-p','require_mission_authorization:=true')
    launch('ch15_safety','readiness_monitor')
    launch('ch15_mission','mission_executor','--ros-args','-p','evidence_dir:='+str(out/'executor'))
    args=['--ros-args','-p','nav_fixture_hold_s:=0.8'] if mode=='cancel' else ['--ros-args','-p','publish_target:=false']
    launch('ch15_adapters','mock_servers',*args);launch('ch15_safety','sensor_watchdog')
    if mode=='invalid_target':
        target=n.create_publisher(TargetObservation,'/ch15/target_observation',profile());timer=n.create_timer(.1,invalid)
    until(lambda:len(ready)>=6 and all(x.ready for x in ready[-6:]) and status,15.)
    assert call(start).success
    if mode=='cancel':
        until(lambda:any(x.event=='GOAL_ACCEPTED' for x in events))
        until(lambda:any(not zero(m) for _,m in motion))
        assert not call(reset).success;assert call(cancel).success
    until(lambda:status and status[-1].state in ('ABORTED','ERROR','COMPLETED'),20.)
    assert status[-1].state=='ABORTED'
    until(lambda:len(motion)>=8 and all(zero(m) for _,m in motion[-8:]))
    assert not status[-1].full_mission_success and not status[-1].is_object_grasped
    assert not call(start).success
    sent=[x for x in events if x.event=='GOAL_SENT'];accepted=[x for x in events if x.event=='GOAL_ACCEPTED'];term=[x for x in events if x.event=='GOAL_TERMINAL'];ends=[x for x in events if x.event=='END']
    assert len(sent)==len(accepted)==len(term)==len(ends)==1
    assert accepted[0].request_id==term[0].request_id and accepted[0].goal_uuid==term[0].goal_uuid
    assert not json.loads(ends[0].detail)['mock_mission_success'] and json.loads(ends[0].detail)['all_terminal']
    assert not any(x.event=='STEP_ENTER' and json.loads(x.detail)['step']=='pick_retract' for x in events)
    if mode=='cancel':
        cs=[x for x in events if x.event=='CANCEL_REQUEST'];acks=[x for x in events if x.event=='CANCEL_ACK']
        assert len(cs)==len(acks)==1 and cs[0].goal_uuid==term[0].goal_uuid and json.loads(acks[0].detail)['matches']
        delay=(term[0].steady_ns-cs[0].steady_ns)/1e9
        assert 0<=delay<=2. and json.loads(term[0].detail)['status']==5
        record('operator_cancel',uuid=term[0].goal_uuid,cancel_to_terminal_s=delay,terminal=5,mission='ABORTED',new_goal_count=0)
    else:
        audit=[json.loads(x) for x in (out/'executor/target-audit.jsonl').read_text().splitlines()]
        assert len(audit)>=3 and all(not x['valid'] and x['reason']=='mission_epoch' for x in audit)
        record('invalid_target',received=len(audit),valid=0,pick_goals=0,mission='ABORTED',navigation_terminal=json.loads(term[0].detail)['status'])
except BaseException as e:err=repr(e);record('FAIL',error=err)
finally:
    for name,p,stream in reversed(children):
        if p.poll() is None:p.send_signal(signal.SIGINT)
        forced=False
        try:rc=p.wait(timeout=6.)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=3);forced=True
        stream.close();exits.append(dict(name=name,exit=rc,forced=forced))
    n.destroy_node();rclpy.try_shutdown()
    clean=all(x['exit']==0 and not x['forced'] for x in exits)
    result=dict(result='PASS' if err is None and clean else 'FAIL',error=err,mode=mode,source='MOCK',full_mission_success=False,rows=rows,processes=exits);(out/'fault-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(mode=mode,result=result['result'],processes=exits)),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
