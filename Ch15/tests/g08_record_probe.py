"""Actual DDS recording with recorder discovery before explicit start."""
import json,os,sys,time,signal,subprocess,hashlib
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from std_msgs.msg import Bool
from sensor_msgs.msg import LaserScan
from ch15_interfaces.msg import MissionStatus,MissionEvent,ReadyState,SafetyState,TargetObservation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from fault_injector import new_receipt
from ch15_adapters.qos_profiles import profile,state_qos,sensor_qos
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'config/g08_record.json').read_text())
mode=sys.argv[1];assert mode in ('F03_transient','F03_persistent','F04','F06','F01')
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False)
fault_receipt=new_receipt(ROOT/'config/g08_faults.yaml',mode.split('_')[0]);targets=[]
children=[];statuses=[];events=[];ready=[];err=None;exits=[];discovered=[];start_wall=None;ready_trace=[];safe_trace=[];stable_since=None;stable_ready_count=0;start_admission=None;scan_trace=[];stop_trace=[];startup_stages=[]
cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=4,'G05 recording requires at least 4 available CPUs'
safety_cpu=str(cpus[0]);recorder_cpu=str(cpus[-1]);worker_cpus=','.join(map(str,cpus[1:-1]))
def spawn(name,args):
    log=(out/(name+'.log')).open('w');affinity=recorder_cpu if name in ('recorder','scan_source') else safety_cpu if name in ('command_arbiter','sensor_watchdog') else worker_cpus
    p=subprocess.Popen(['taskset','-c',affinity,*args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((name,p,log));return p
def launch(pkg,exe,*args):
    return spawn(exe,[str(Path(os.environ['G03_INSTALL'])/pkg/'lib'/pkg/exe),*args])
rclpy.init();n=Node('g08_record_probe')
n.create_subscription(MissionStatus,'/ch15/mission_state',statuses.append,state_qos)
n.create_subscription(MissionEvent,'/ch15/mission_event',events.append,profile(100))
n.create_subscription(TargetObservation,'/ch15/target_observation',lambda m:targets.append(dict(epoch=m.epoch,mission_id=m.mission_id,stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,wall_ns=time.monotonic_ns())),profile())
def on_ready(m):
    ready.append(m);ready_trace.append(dict(wall_ns=time.monotonic_ns(),stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,ready=m.ready,missing=list(m.missing)))
def on_safety(m):
    safe_trace.append(dict(wall_ns=time.monotonic_ns(),stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,latched=m.latched,blocked=m.blocked,reason=m.reason,owner=m.owner))
n.create_subscription(ReadyState,'/ch15/ready',on_ready,profile())
n.create_subscription(SafetyState,'/ch15/safety_state',on_safety,state_qos)
n.create_subscription(LaserScan,'/scan',lambda m:scan_trace.append(dict(wall_ns=time.monotonic_ns(),stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,valid=bool(m.ranges) and m.header.frame_id=='base_link')),sensor_qos)
n.create_subscription(Bool,'/ch15/stop_request',lambda m:stop_trace.append(dict(wall_ns=time.monotonic_ns(),stop=m.data)),profile(10))
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
    return set(discovered)==set(cfg['required']) and n.count_publishers('/scan')==1 and n.count_publishers('/ch15/target_observation')==1
def admission():
    global stable_since,stable_ready_count,start_admission
    now=time.monotonic_ns()
    if safe_trace and safe_trace[-1]['latched']:raise RuntimeError('startup safety latch; no reset')
    ros_now=n.get_clock().now().nanoseconds
    good=graph() and start.service_is_ready() and statuses and len(ready_trace)>=3 and all(x['ready'] for x in ready_trace[-3:]) and 0<=now-ready_trace[-1]['wall_ns']<=250_000_000 and safe_trace and 0<=now-safe_trace[-1]['wall_ns']<=150_000_000 and 0<=ros_now-ready_trace[-1]['stamp_ns']<=300_000_000 and 0<=ros_now-safe_trace[-1]['stamp_ns']<=150_000_000 and not safe_trace[-1]['latched'] and safe_trace[-1]['owner']=='MOCK:ch15_command_arbiter'
    if not good:stable_since=None;return False
    if stable_since is None:stable_since=now;stable_ready_count=len(ready_trace)
    if now-stable_since>=600_000_000 and len(ready_trace)-stable_ready_count>=5:
        start_admission=dict(stable_ns=now-stable_since,new_ready_samples=len(ready_trace)-stable_ready_count,ready=ready_trace[-1],safety=safe_trace[-1]);return True
    return False
def stage(name):
    startup_stages.append(dict(stage=name,wall_ns=time.monotonic_ns()))
def scan_stable():
    if len(scan_trace)<6:return False
    a=scan_trace[-6:]
    return all(x['valid'] for x in a) and all(0<b['stamp_ns']-c['stamp_ns']<=200_000_000 and 0<b['wall_ns']-c['wall_ns']<=200_000_000 for c,b in zip(a,a[1:])) and a[-1]['wall_ns']-a[0]['wall_ns']>=400_000_000 and 0<=time.monotonic_ns()-a[-1]['wall_ns']<=200_000_000 and 0<=n.get_clock().now().nanoseconds-a[-1]['stamp_ns']<=200_000_000
def heartbeat_stable():
    if len(stop_trace)<8:return False
    a=stop_trace[-8:]
    return all(not x['stop'] for x in a) and all(0<b['wall_ns']-c['wall_ns']<=100_000_000 for c,b in zip(a,a[1:])) and a[-1]['wall_ns']-a[0]['wall_ns']>=300_000_000 and 0<=time.monotonic_ns()-a[-1]['wall_ns']<=100_000_000
try:
    graph_before=n.get_node_names_and_namespaces()
    stage('preflight_graph')
    (out/'preflight_graph.json').write_text(json.dumps(graph_before,indent=2)+'\n')
    assert all(name==n.get_name() and namespace==n.get_namespace() for name,namespace in graph_before) and len(graph_before)<=1,('domain not empty',graph_before)
    spawn('recorder',['ros2','bag','record','--storage','mcap','--storage-config-file',str(ROOT/'config/mcap_storage.yaml'),'--max-bag-size',str(cfg['split_bytes']),'--qos-profile-overrides-path',str(ROOT/'config/g08_bag_qos.yaml'),'-o',str(out/'bag'),'--topics',*cfg['required']])
    until(lambda:'rosbag2_recorder' in n.get_node_names(),10)
    stage('recorder_ready')
    os.sched_setaffinity(0,set(cpus[1:-1]))
    spawn('scan_source',[sys.executable,str(ROOT/'tests/g05_scan_diag.py'),'producer',str(out/'scan_source_trace.json'),'isolated','F01' if mode=='F01' else 'normal'])
    until(scan_stable,15);stage('isolated_scan_stable')
    launch('ch15_safety','readiness_monitor')
    launch('ch15_mission','recovery_executor','--ros-args','-p','evidence_dir:='+str(out/'executor'))
    spawn('mock_servers',[sys.executable,str(ROOT/'tests/g08_fault_fixture.py'),mode,str(out/'mock_native_trace.json'),'--ros-args','-p','nav_fixture_hold_s:=2.0' if mode=='F01' else 'nav_fixture_hold_s:=0.0','-p','publish_scan:=false','-p','publish_target:=false'])
    until(scan_stable,15);stage('scan_stable')
    spawn('sensor_watchdog',[sys.executable,str(ROOT/'tests/g05_safety_trace.py'),'watchdog',str(out/'watchdog_native_trace.json')])
    until(heartbeat_stable,10);stage('heartbeat_stable')
    spawn('command_arbiter',[sys.executable,str(ROOT/'tests/g05_safety_trace.py'),'arbiter',str(out/'arbiter_native_trace.json'),'--ros-args','-p','require_mission_authorization:=true'])
    until(admission,20);stage('mission_admission')
    assert not events
    start_wall=time.monotonic_ns();f=start.call_async(Trigger.Request());until(f.done,4)
    assert f.result().success,('start_request_rejected',f.result().message)
    until(lambda:statuses and statuses[-1].state in ('COMPLETED','ABORTED','ERROR'),30)
    expected='COMPLETED' if mode=='F03_transient' else 'ABORTED'
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
    (out/'target_observed.json').write_text(json.dumps(targets,indent=2)+'\n')
    (out/'fault_receipt.json').write_text(json.dumps(fault_receipt,indent=2)+'\n')
    (out/'readiness_trace.json').write_text(json.dumps(ready_trace,indent=2)+'\n')
    (out/'safety_trace.json').write_text(json.dumps(safe_trace,indent=2)+'\n')
    (out/'scan_trace.json').write_text(json.dumps(scan_trace,indent=2)+'\n')
    (out/'stop_trace.json').write_text(json.dumps(stop_trace,indent=2)+'\n')
    (out/'startup_stages.json').write_text(json.dumps(dict(stages=startup_stages,affinity=dict(safety=safety_cpu,recorder=recorder_cpu,workers=worker_cpus)),indent=2)+'\n')
    result=dict(result='PASS' if err is None and len(exits)==7 and all(x['exit']==0 and not x['forced'] for x in exits) and size()<=cfg['max_bytes'] else 'FAIL',mode=mode,source='MOCK',error=err,discovered=discovered,start_admission=start_admission,start_wall_ns=start_wall,terminal=statuses[-1].state if statuses else None,observed_events=len(events),processes=exits,bag_bytes=size(),full_mission_success=False)
    (out/'record_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
