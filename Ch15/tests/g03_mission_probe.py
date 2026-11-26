"""Normal actual ROS process integration, exactly one full mission."""
import csv,json,math,os,pathlib,signal,subprocess,sys,time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from geometry_msgs.msg import Twist
from ch15_interfaces.msg import MissionStatus,MissionEvent,ReadyState
from ch15_adapters.qos_profiles import profile,state_qos
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
children=[];rows=[];status=[];events=[];ready=[];motion=[]
def launch(pkg,exe,*args):
    p=pathlib.Path(os.environ['G03_INSTALL'])/pkg/'lib'/pkg/exe
    stream=(out/(exe+'.log')).open('w')
    child=subprocess.Popen([str(p),*args],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    children.append((exe,child,stream))
def record(label,**kw):
    row=dict(label=label,**kw);rows.append(row);print(json.dumps(row),flush=True)
rclpy.init();n=Node('g03_mission_probe')
subs=[n.create_subscription(MissionStatus,'/ch15/mission_state',status.append,state_qos),n.create_subscription(MissionEvent,'/ch15/mission_event',events.append,profile(100)),n.create_subscription(ReadyState,'/ch15/ready',ready.append,profile()),n.create_subscription(Twist,'/cmd_vel',motion.append,profile())]
start=n.create_client(Trigger,'/ch15/start_mission');reset=n.create_client(Trigger,'/ch15/reset_safety');cancel=n.create_client(Trigger,'/ch15/cancel_mission')
def until(pred,seconds=10.):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        for name,p,_ in children:assert p.poll() is None,(name,p.returncode)
        rclpy.spin_once(n,timeout_sec=.02)
        if pred():return
    raise AssertionError('deadline '+str(rows[-1] if rows else 'startup')+' state='+str(status[-1].state if status else None))
def spin_for(s):
    end=time.monotonic()+s
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.02)
def call(c):
    until(c.service_is_ready);f=c.call_async(Trigger.Request());until(f.done);return f.result()
def zero(m):return all(abs(x)<=1e-9 for x in (m.linear.x,m.linear.y,m.linear.z,m.angular.x,m.angular.y,m.angular.z))
err=None;exits=[]
try:
    launch('ch15_safety','command_arbiter','--ros-args','-p','require_mission_authorization:=true')
    launch('ch15_safety','readiness_monitor')
    launch('ch15_mission','mission_executor','--ros-args','-p','evidence_dir:='+str(out/'executor'))
    until(start.service_is_ready);assert not call(start).success;record('unready_start_rejected')
    launch('ch15_adapters','mock_servers');launch('ch15_safety','sensor_watchdog')
    t0=time.monotonic()
    until(lambda:len(ready)>=3 and all(x.ready for x in ready[-3:]) and len(status)>=3,15.)
    spin_for(.35)
    assert not events and all(zero(m) for m in motion)
    record('ready_without_auto_start',elapsed_s=time.monotonic()-t0,zero_samples=len(motion))
    assert call(start).success;assert not call(start).success
    until(lambda:any(x.event=='GOAL_ACCEPTED' for x in events))
    assert not call(reset).success;record('active_reset_rejected')
    until(lambda:status and status[-1].state in ('COMPLETED','ABORTED','ERROR'),60.)
    assert status[-1].state=='COMPLETED',status[-1].state
    spin_for(.5)
    assert not call(start).success;assert not call(cancel).success
    assert not status[-1].full_mission_success and not status[-1].is_object_grasped
    assert all(zero(m) for m in motion[-8:]) and any(not zero(m) for m in motion)
    trace=[json.loads(x.detail) for x in events if x.event=='STEP_ENTER']
    expected=['ready','navigate','detect','approach_stand','pick_retract','return_home','place','verify_finish']
    assert [x['step'] for x in trace]==expected,trace
    ends=[json.loads(x.detail) for x in events if x.event=='END'];assert len(ends)==1 and ends[0]['mock_mission_success'] and ends[0]['all_terminal'] and ends[0]['steps']==expected
    sent=[x for x in events if x.event=='GOAL_SENT'];accepted=[x for x in events if x.event=='GOAL_ACCEPTED'];terminal=[x for x in events if x.event=='GOAL_TERMINAL']
    assert len(sent)==len(accepted)==len(terminal)==4
    assert {(x.request_id,x.goal_uuid) for x in accepted}=={(x.request_id,x.goal_uuid) for x in terminal} and len({x.goal_uuid for x in accepted})==4
    assert all(json.loads(x.detail)['status']==4 for x in terminal)
    assert sum(x.event=='START' for x in events)==1
    assert [x.event_seq for x in events]==list(range(1,len(events)+1))
    end_seq=[x.event_seq for x in events if x.event=='END'][0];assert not any(x.event=='GOAL_SENT' and x.event_seq>end_seq for x in events)
    states=[]
    for s in status:
        if not states or states[-1]!=s.state:states.append(s.state)
    assert states==['IDLE','NAVIGATING','SEARCHING','APPROACHING','MANIPULATING','RETURNING','PLACING','COMPLETED'],states
    with (out/'executor/ticks.csv').open() as f:ticks=list(csv.DictReader(f))
    durations=sorted(float(x['duration_ms']) for x in ticks);p95=durations[math.ceil(.95*len(durations))-1];maximum=max(durations)
    ns=[int(x['steady_ns']) for x in ticks];hz=(len(ns)-1)*1e9/(ns[-1]-ns[0])
    assert len(ticks)>=30 and p95<=20. and maximum<=100. and 9.<=hz<=11.,(len(ticks),p95,maximum,hz)
    record('MOCK_MISSION_PASS',steps=expected,states=states,terminal_count=1,goals=len(sent),uuid_terminal_matches=len(terminal),tick_count=len(ticks),tick_p95_ms=p95,tick_max_ms=maximum,tick_hz=hz,full_mission_success=False)
    old=status[-1].mission_id;epoch=status[-1].epoch
    assert call(reset).success
    until(lambda:status[-1].mission_id!=old and status[-1].epoch==epoch+1 and status[-1].state=='IDLE')
    spin_for(.3);assert sum(x.event=='START' for x in events)==1
    record('explicit_reset_new_epoch',epoch=status[-1].epoch,new_mission_id=status[-1].mission_id)
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
    result=dict(result='PASS' if err is None and clean else 'FAIL',error=err,source='MOCK',full_mission_success=False,rows=rows,processes=exits)
    (out/'mission-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(processes=exits,result=result['result'])),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
