"""R03 controlled ROS /clock only, no real clock mutation or robot motion."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Time
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist,TwistStamped
from std_msgs.msg import Bool
from ch15_interfaces.msg import ReadyState,SafetyState
from ch15_adapters.qos_profiles import profile,state_qos,sensor_qos
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from fault_injector import new_receipt
out=Path(sys.argv[1]);mode=sys.argv[2]
assert mode in ('forward','rewind')
out.mkdir(exist_ok=False)
receipt=new_receipt(ROOT/'config/g08_faults.yaml','F10')
receipt.update(mode=mode,physical_motion=False,system_clock_modified=False,result='FAIL',processes=[])
trace=[];children=[];rclpy.init();n=Node('g09_clock_guard_fixture')
BASE=10_000_000_000
JUMP=2_927_308_797 if mode=='forward' else -500_000_000
ros_ns=BASE;scan_ns=BASE;scan_enabled=False;cmd_enabled=False
last_pump=0
def emit(kind,**kw):
    t=time.monotonic_ns();trace.append(dict(kind=kind,wall_ns=t,**kw));return t
def rows(kind):return [r for r in trace if r['kind']==kind]
def stamp(v):return Time(sec=v//10**9,nanosec=v%10**9)
cl=n.create_publisher(Clock,'/clock',10)
sc=n.create_publisher(LaserScan,'/scan',sensor_qos)
rd=n.create_publisher(ReadyState,'/ch15/ready',profile())
cm=n.create_publisher(TwistStamped,'/ch15/cmd_vel_in',profile())
mb=n.create_publisher(Bool,'/ch15/mission_block',profile(10))
n.create_subscription(Bool,'/ch15/stop_request',lambda m:emit('guard',stop=m.data),profile(10))
n.create_subscription(SafetyState,'/ch15/safety_state',lambda m:emit('safety',latched=m.latched,blocked=m.blocked,reason=m.reason),state_qos)
n.create_subscription(Twist,'/cmd_vel',lambda m:emit('output',zero=all(v==0. for v in (m.linear.x,m.linear.y,m.linear.z,m.angular.x,m.angular.y,m.angular.z)),vx=m.linear.x),profile())
def spawn(mode):
    log=(out/(mode+'.log')).open('w')
    args=[sys.executable,str(ROOT/'tests/g08_safety_trace.py'),mode,str(out/(mode+'_native_trace.json')),'--ros-args','-p','use_sim_time:=true']
    if mode=='arbiter':args+=['-p','require_mission_authorization:=true']
    p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((mode,p,log))
def pump():
    global last_pump
    now=time.monotonic_ns()
    if now-last_pump<30_000_000:return
    last_pump=now
    cl.publish(Clock(clock=stamp(ros_ns)));emit('clock_sent',ros_ns=ros_ns)
    if scan_enabled:
        s=LaserScan();s.header.frame_id='base_link';s.header.stamp=stamp(scan_ns);s.range_min=.05;s.range_max=5.;s.ranges=[2.,2.,2.]
        sc.publish(s);emit('scan_sent',stamp_ns=scan_ns)
    if cmd_enabled:
        r=ReadyState();r.header.stamp=stamp(ros_ns);r.ready=True;rd.publish(r)
        c=TwistStamped();c.header.stamp=stamp(ros_ns);c.header.frame_id='base_link';c.twist.linear.x=.1;cm.publish(c)
        mb.publish(Bool(data=False));emit('command_sent',stamp_ns=ros_ns,vx=.1)
def wait(pred,seconds=4):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        assert all(p.poll() is None for _,p,_ in children),'child exited'
        pump();rclpy.spin_once(n,timeout_sec=.005)
        if pred():return
    raise RuntimeError('deadline')
def stop():
    for name,p,log in reversed(children):
        forced=False
        if p.poll() is None:p.send_signal(signal.SIGINT)
        try:rc=p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=3);forced=True
        log.close();receipt['processes'].append(dict(name=name,exit=rc,forced=forced))
try:
    graph=n.get_node_names_and_namespaces()
    assert all(x==(n.get_name(),n.get_namespace()) for x in graph) and len(graph)<=1,graph
    spawn('watchdog')
    wait(lambda:cl.get_subscription_count()==1 and sc.get_subscription_count()==1 and n.count_publishers('/ch15/stop_request')==1,8)
    begin=time.monotonic();wait(lambda:time.monotonic()-begin>=.2,1)
    assert not rows('guard'),'guard clear emitted before first scan'
    scan_enabled=True
    wait(lambda:len(rows('guard'))>=5,3)
    assert not any(r['stop'] for r in rows('guard'))
    spawn('arbiter')
    wait(lambda:cl.get_subscription_count()==2 and all(p.get_subscription_count()==1 for p in (rd,cm,mb)) and n.count_publishers('/cmd_vel')==1,8)
    cmd_enabled=True
    wait(lambda:len([r for r in rows('output') if not r['zero']])>=5,3)
    assert not any(r['latched'] for r in rows('safety')) and not any(r['stop'] for r in rows('guard'))
    trigger=emit('injection',old_ros_ns=BASE,new_ros_ns=BASE+JUMP,old_scan_stamp_ns=BASE)
    ros_ns=BASE+JUMP;last_pump=0
    wait(lambda:any(r['stop'] for r in rows('guard')) and any(r['latched'] for r in rows('safety')),1)
    g=next(r for r in rows('guard') if r['stop']);a=next(r for r in rows('safety') if r['latched'])
    assert a['blocked']
    wait(lambda:any(r['zero'] and r['wall_ns']>=a['wall_ns'] for r in rows('output')),1)
    z=next(r for r in rows('output') if r['zero'] and r['wall_ns']>=a['wall_ns'])
    assert 0<=(g['wall_ns']-trigger)/1e9<=.15
    assert 0<=(a['wall_ns']-trigger)/1e9<=.25
    assert 0<=(z['wall_ns']-a['wall_ns'])/1e9<=.10
    # Restored fresh scan in the new ROS epoch; safety must not auto-clear.
    scan_ns=ros_ns;resume=emit('fresh_scan_restored',stamp_ns=scan_ns);last_pump=0
    wait(lambda:len([r for r in rows('output') if r['wall_ns']>=resume])>=10 and len([r for r in rows('guard') if r['wall_ns']>=resume])>=10,2)
    assert all(r['zero'] for r in rows('output') if r['wall_ns']>=z['wall_ns'])
    assert all(r['latched'] and r['blocked'] for r in rows('safety') if r['wall_ns']>=a['wall_ns'])
    assert all(r['stop'] for r in rows('guard') if r['wall_ns']>=g['wall_ns'])
    receipt['measurements']=dict(injected_ros_step_ns=JUMP,trigger_to_guard_observed_s=(g['wall_ns']-trigger)/1e9,trigger_to_latch_observed_s=(a['wall_ns']-trigger)/1e9,latch_to_later_zero_observed_s=(z['wall_ns']-a['wall_ns'])/1e9,post_resume_nonzero=0,post_resume_clear=0,positive_outputs_before_step=sum(not r['zero'] for r in rows('output') if r['wall_ns']<trigger))
    receipt['injection_observed']=True
except BaseException as e:
    receipt['error']=repr(e);raise
finally:
    try:stop()
    finally:
        n.destroy_node();rclpy.try_shutdown()
        (out/'trace.json').write_text(json.dumps(trace,indent=2)+'\n')
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert len(receipt['processes'])==2 and all(x['exit']==0 and not x['forced'] for x in receipt['processes'])
watch=json.loads((out/'watchdog_native_trace.json').read_text())['events']
first=next(r for r in watch if r.get('first_latch'))
assert first['source_stamp_ns']==BASE and 0<=first['age_s']<=.2,first
assert any(r['kind']=='scan' and r['valid'] and r['stamp_ns']==BASE+JUMP for r in watch)
assert all(r['latched'] for r in watch if r['kind']=='watchdog' and r['wall_ns']>=first['wall_ns'])
arb=json.loads((out/'arbiter_native_trace.json').read_text())['events']
block=next(r for r in arb if r['kind']=='blocked' and r['latched'] and r['value'])
zero=next(r for r in arb if r['kind']=='publish' and r['topic']=='/cmd_vel' and r['publish_enter_ns']>=block['wall_ns'])
assert zero['zero']
gap=(zero['wall_ns']-block['wall_ns'])/1e9;assert 0<=gap<=.1,gap
receipt['measurements'].update(native_receipt_age_s=first['age_s'],native_block_to_zero_publish_s=gap)
receipt['result']='PASS'
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
