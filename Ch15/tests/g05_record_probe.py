"""Actual DDS recording with recorder discovery before explicit start."""
import json,os,sys,time,signal,subprocess,hashlib
from pathlib import Path
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from ch15_interfaces.msg import MissionStatus,MissionEvent,ReadyState
from ch15_adapters.qos_profiles import profile,state_qos
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'config/g05_record.json').read_text())
mode=sys.argv[1];assert mode in ('normal','F01','F06')
out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False)
children=[];statuses=[];events=[];ready=[];err=None;exits=[];discovered=[];start_wall=None
def spawn(name,args):
    log=(out/(name+'.log')).open('w');p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((name,p,log));return p
def launch(pkg,exe,*args):
    return spawn(exe,[str(Path(os.environ['G03_INSTALL'])/pkg/'lib'/pkg/exe),*args])
rclpy.init();n=Node('g05_record_probe')
n.create_subscription(MissionStatus,'/ch15/mission_state',statuses.append,state_qos)
n.create_subscription(MissionEvent,'/ch15/mission_event',events.append,profile(100))
n.create_subscription(ReadyState,'/ch15/ready',ready.append,profile())
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
try:
    assert not n.get_node_names_and_namespaces() or set(n.get_node_names())<= {'g05_record_probe'},'domain not empty'
    spawn('recorder',['ros2','bag','record','--storage','mcap','--storage-config-file',str(ROOT/'config/mcap_storage.yaml'),'--max-bag-size',str(cfg['split_bytes']),'--qos-profile-overrides-path',str(ROOT/'config/bag_qos.yaml'),'-o',str(out/'bag'),*cfg['required']])
    until(lambda:'rosbag2_recorder' in n.get_node_names(),10)
    launch('ch15_safety','command_arbiter','--ros-args','-p','require_mission_authorization:=true')
    launch('ch15_safety','readiness_monitor')
    launch('ch15_mission','mission_executor','--ros-args','-p','evidence_dir:='+str(out/'executor'))
    if mode=='normal':launch('ch15_adapters','mock_servers')
    else:spawn('fault_fixture',[sys.executable,str(ROOT/'tests/g05_fault_fixture.py'),mode,'--ros-args','-p','nav_fixture_hold_s:=2.0' if mode=='F01' else 'nav_fixture_hold_s:=0.0'])
    launch('ch15_safety','sensor_watchdog')
    until(lambda:graph() and len(ready)>=3 and all(x.ready for x in ready[-3:]) and statuses and start.service_is_ready(),20)
    assert not events
    start_wall=time.monotonic_ns();f=start.call_async(Trigger.Request());until(f.done,4);assert f.result().success
    until(lambda:statuses and statuses[-1].state in ('COMPLETED','ABORTED','ERROR'),30)
    expected='COMPLETED' if mode=='normal' else 'ABORTED'
    assert statuses[-1].state==expected,(mode,statuses[-1].state)
    until(lambda:any(e.event=='END' for e in events),3)
    # Drain end/status with recorder still alive.
    deadline=time.monotonic()+.5
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
    result=dict(result='PASS' if err is None and len(exits)==6 and all(x['exit']==0 and not x['forced'] for x in exits) and size()<=cfg['max_bytes'] else 'FAIL',mode=mode,source='MOCK',error=err,discovered=discovered,start_wall_ns=start_wall,terminal=statuses[-1].state if statuses else None,observed_events=len(events),processes=exits,bag_bytes=size(),full_mission_success=False)
    (out/'record_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
sys.exit(0 if result['result']=='PASS' else 1)
