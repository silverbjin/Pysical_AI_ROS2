"""Actual DDS recording with recorder discovery before explicit start."""
import json,os,sys,time,signal,subprocess,hashlib
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from ch15_interfaces.msg import MissionStatus,MissionEvent,ReadyState,SafetyState
from ch15_adapters.qos_profiles import profile,state_qos
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'config/g05_record.json').read_text())
mode=sys.argv[1];assert mode in ('normal','F01','F06')
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False)
children=[];statuses=[];events=[];ready=[];err=None;exits=[];discovered=[];start_wall=None;ready_trace=[];safe_trace=[];stable_since=None;stable_ready_count=0;start_admission=None
def spawn(name,args):
    log=(out/(name+'.log')).open('w');p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((name,p,log));return p
def launch(pkg,exe,*args):
    return spawn(exe,[str(Path(os.environ['G03_INSTALL'])/pkg/'lib'/pkg/exe),*args])
rclpy.init();n=Node('g05_record_probe')
n.create_subscription(MissionStatus,'/ch15/mission_state',statuses.append,state_qos)
n.create_subscription(MissionEvent,'/ch15/mission_event',events.append,profile(100))
def on_ready(m):
    ready.append(m);ready_trace.append(dict(wall_ns=time.monotonic_ns(),stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,ready=m.ready,missing=list(m.missing)))
def on_safety(m):
    safe_trace.append(dict(wall_ns=time.monotonic_ns(),stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,latched=m.latched,blocked=m.blocked,reason=m.reason,owner=m.owner))
n.create_subscription(ReadyState,'/ch15/ready',on_ready,profile())
n.create_subscription(SafetyState,'/ch15/safety_state',on_safety,state_qos)
start=n.create_client(Trigger,'/ch15/start_mission')
begin=time.monotonic()
def size():return sum(p.stat().st_size for p in (out/'bag').rglob('*') if p.is_file())
def until(pred,seconds):
    end=min(time.monotonic()+seconds,begin+cfg['max_wall_s'])
    while time.monotonic()<end:
        assert all(p.poll() is None for _,p,_ in children),'child exited'
        assert size()<=cfg['max_bytes'],'archive limit exceeded'
        rclpy.spin_once(n,timeout_sec=.02)
        if pred():return
    raise RuntimeError('deadline')
def graph():
    discovered[:]=[t for t in cfg['required'] if any(x.node_name=='rosbag2_recorder' for x in n.get_subscriptions_info_by_topic(t)) and n.count_publishers(t)>0]
    return set(discovered)==set(cfg['required'])
def admission():
    global stable_since,stable_ready_count,start_admission
    now=time.monotonic_ns()
    good=graph() and start.service_is_ready() and statuses and len(ready_trace)>=3 and all(x['ready'] for x in ready_trace[-3:]) and 0<=now-ready_trace[-1]['wall_ns']<=250_000_000 and safe_trace and 0<=now-safe_trace[-1]['wall_ns']<=150_000_000 and not safe_trace[-1]['latched'] and safe_trace[-1]['owner']=='MOCK:ch15_command_arbiter'
    if not good:stable_since=None;return False
    if stable_since is None:stable_since=now;stable_ready_count=len(ready_trace)
    if now-stable_since>=600_000_000 and len(ready_trace)-stable_ready_count>=5:
        start_admission=dict(stable_ns=now-stable_since,new_ready_samples=len(ready_trace)-stable_ready_count,ready=ready_trace[-1],safety=safe_trace[-1]);return True
    return False
try:
    assert not n.get_node_names_and_namespaces() or set(n.get_node_names())<= {'g05_record_probe'},'domain not empty'
    spawn('recorder',['ros2','bag','record','--storage','mcap','--storage-config-file',str(ROOT/'config/mcap_storage.yaml'),'--max-bag-size',str(cfg['split_bytes']),'--qos-profile-overrides-path',str(ROOT/'config/bag_qos.yaml'),'-o',str(out/'bag'),'--topics',*cfg['required']])
    until(lambda:'rosbag2_recorder' in n.get_node_names(),10)
    launch('ch15_safety','command_arbiter','--ros-args','-p','require_mission_authorization:=true')
    launch('ch15_safety','readiness_monitor')
    launch('ch15_mission','mission_executor','--ros-args','-p','evidence_dir:='+str(out/'executor'))
    if mode=='normal':launch('ch15_adapters','mock_servers')
    else:spawn('fault_fixture',[sys.executable,str(ROOT/'tests/g05_fault_fixture.py'),mode,'--ros-args','-p','nav_fixture_hold_s:=2.0' if mode=='F01' else 'nav_fixture_hold_s:=0.0'])
    launch('ch15_safety','sensor_watchdog')
    until(admission,20)
    assert not events
    start_wall=time.monotonic_ns();f=start.call_async(Trigger.Request());until(f.done,4);assert f.result().success
    until(lambda:statuses and statuses[-1].state in ('COMPLETED','ABORTED','ERROR'),30)
    expected='COMPLETED' if mode=='normal' else 'ABORTED'
    until(lambda:any(e.event=='END' for e in events),3)
    assert statuses[-1].state==expected,(mode,statuses[-1].state)
    # Drain end/status with recorder still alive.
    deadline=time.monotonic()+(1.2 if mode=='F01' else .5)
    until(lambda:time.monotonic()>=deadline,2)
except BaseException as e:err=repr(e)
finally:
    # All producers stop first, recorder closes last.
    for name,p,log in reversed(children):
        if p.poll() is None:p.send_signal(signal.SIGINT)
        forced=False
        try:rc=p.wait(timeout=8)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=3);forced=True
        log.close();exits.append(dict(name=name,exit=rc,forced=forced))
    n.destroy_node();rclpy.try_shutdown()
    (out/'readiness_trace.json').write_text(json.dumps(ready_trace,indent=2)+'\n')
    (out/'safety_trace.json').write_text(json.dumps(safe_trace,indent=2)+'\n')
    result=dict(result='PASS' if err is None and len(exits)==6 and all(x['exit']==0 and not x['forced'] for x in exits) and size()<=cfg['max_bytes'] else 'FAIL',mode=mode,source='MOCK',error=err,discovered=discovered,start_admission=start_admission,start_wall_ns=start_wall,terminal=statuses[-1].state if statuses else None,observed_events=len(events),processes=exits,bag_bytes=size(),full_mission_success=False)
    (out/'record_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
