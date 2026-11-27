"""Actual DDS boundary witness using installed original mock safety nodes.
No physical simulator, no Nav2 goal, no claimed complete mission.
"""
import sys,time,signal,os,json,subprocess
from pathlib import Path
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_prefix
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist,TwistStamped
from std_msgs.msg import Bool
from ch15_interfaces.msg import ReadyState,SafetyState
from ch15_adapters.qos_profiles import profile,sensor_qos,state_qos
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from fault_injector import new_receipt

out=Path(sys.argv[1]);mode=sys.argv[2]
assert mode in ('F01_receipt','F01_source','F07')
root=Path(__file__).resolve().parents[1]
receipt=new_receipt(root/'config/g08_faults.yaml','F07' if mode=='F07' else 'F01')
receipt.update(mode=mode,measurements={},processes=[])
trace=[];proc=None
rclpy.init();n=Node('g08_boundary_fixture')
def emit(kind,**kw):
    row=dict(kind=kind,wall_ns=time.monotonic_ns(),**kw);trace.append(row);return row['wall_ns']
def rows(kind):return [x for x in trace if x['kind']==kind]
def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.005)
def wait(fn,seconds=4,pump=None):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if pump:pump()
        rclpy.spin_once(n,timeout_sec=.005)
        if fn():return
    raise RuntimeError('deadline')
def launch(exe,args):
    global proc
    path=Path(get_package_prefix('ch15_safety'))/'lib/ch15_safety'/exe
    proc=subprocess.Popen([str(path),*args],start_new_session=True)
def stop():
    global proc
    if proc:
        os.killpg(proc.pid,signal.SIGINT)
        try:rc=proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise
        proc=None;receipt['processes'].append(rc)
        assert rc==0
def stamp(ns):
    from builtin_interfaces.msg import Time
    return Time(sec=ns//10**9,nanosec=ns%10**9)
try:
    if mode.startswith('F01'):
        cp=n.create_publisher(Clock,'/clock',10)
        sp=n.create_publisher(LaserScan,'/scan',sensor_qos)
        n.create_subscription(Bool,'/ch15/stop_request',lambda m:emit('stop',value=m.data),profile(10))
        launch('sensor_watchdog',['--ros-args','-p','use_sim_time:=true'])
        wait(lambda:cp.get_subscription_count()==1 and sp.get_subscription_count()==1 and n.count_publishers('/ch15/stop_request')==1,8)
        def clock(ns):
            c=Clock();c.clock=stamp(ns);cp.publish(c);emit('clock',ros_ns=ns)
        def scan():
            s=LaserScan();s.header.stamp=stamp(10*10**9);s.header.frame_id='base_link'
            s.range_min=.05;s.range_max=5.;s.ranges=[2.,2.,2.];sp.publish(s);return emit('scan_sent')
        clock(10*10**9);spin(.1)
        assert not rows('stop'),'watchdog must not emit clear before first scan'
        for _ in range(5):scan();spin(.07)
        assert len([r for r in rows('stop') if not r['value']])>=3 and not any(r['value'] for r in rows('stop'))
        last=rows('scan_sent')[-1]['wall_ns']
        trigger=emit('injection',mode=mode)
        if mode=='F01_source':
            clock(10_400_000_000)
        wait(lambda:any(r['value'] for r in rows('stop')),1.4)
        first=next(r['wall_ns'] for r in rows('stop') if r['value'])
        delta=(first-last)/1e9
        if mode=='F01_receipt':assert 0.95<=delta<=1.15,delta
        else:assert 0<=delta<1.0 and (first-trigger)/1e9<=.15,delta
        # New valid scan in original clock domain cannot clear latch.
        clock(10*10**9);spin(.05)
        before=len(rows('stop'))
        for _ in range(5):scan();spin(.06)
        resumed=rows('stop')[before:]
        assert resumed and all(r['value'] for r in resumed)
        receipt['measurements']=dict(last_scan_publish_to_guard_s=delta,trigger_to_guard_s=(first-trigger)/1e9,post_resume_clear=0,clock_paused=mode=='F01_receipt',first_sample_clear=False)
        receipt['injection_observed']=True
    else:
        hp=n.create_publisher(Bool,'/ch15/stop_request',profile(10))
        rp=n.create_publisher(ReadyState,'/ch15/ready',profile())
        cp=n.create_publisher(TwistStamped,'/ch15/cmd_vel_in',profile())
        mp=n.create_publisher(Bool,'/ch15/mission_block',profile(10))
        n.create_subscription(Twist,'/cmd_vel',lambda m:emit('output',vx=m.linear.x,zero=all(x==0. for x in (m.linear.x,m.linear.y,m.linear.z,m.angular.x,m.angular.y,m.angular.z))),profile())
        n.create_subscription(SafetyState,'/ch15/safety_state',lambda m:emit('safety',blocked=m.blocked,latched=m.latched,owner=m.owner),state_qos)
        launch('command_arbiter',['--ros-args','-p','require_mission_authorization:=true'])
        wait(lambda:all(p.get_subscription_count()==1 for p in (hp,rp,cp,mp)) and n.count_publishers('/cmd_vel')==1,8)
        send_at=0.;heartbeat=False
        def pump():
            global send_at
            if time.monotonic()-send_at<.03:return
            send_at=time.monotonic()
            st=n.get_clock().now().to_msg()
            r=ReadyState();r.header.stamp=st;r.ready=True;rp.publish(r)
            c=TwistStamped();c.header.stamp=st;c.header.frame_id='base_link';c.twist.linear.x=.1;cp.publish(c)
            mp.publish(Bool(data=False))
            if heartbeat:hp.publish(Bool(data=False));emit('heartbeat_sent')
        wait(lambda:len(rows('output'))>=4,2,pump)
        assert all(x['zero'] for x in rows('output'))
        heartbeat=True
        wait(lambda:len([x for x in rows('output') if not x['zero']])>=5,3,pump)
        heartbeat=False
        last=rows('heartbeat_sent')[-1]['wall_ns'];trigger=emit('injection',mode=mode)
        wait(lambda:any(x['latched'] for x in rows('safety')),1,pump)
        latch=next(x['wall_ns'] for x in rows('safety') if x['latched'])
        wait(lambda:any(x['zero'] and x['wall_ns']>=trigger for x in rows('output')),1,pump)
        zero=next(x['wall_ns'] for x in rows('output') if x['zero'] and x['wall_ns']>=trigger)
        assert 0<=(latch-last)/1e9<=.25,(latch-last)/1e9
        assert 0<=(zero-last)/1e9<=.25,(zero-last)/1e9
        assert abs(zero-latch)/1e9<=.10
        begin=time.monotonic_ns();heartbeat=True
        wait(lambda:len([x for x in rows('output') if x['wall_ns']>begin])>=10,2,pump)
        assert all(x['zero'] for x in rows('output') if x['wall_ns']>=zero)
        assert all(x['latched'] for x in rows('safety') if x['wall_ns']>=latch)
        receipt['measurements']=dict(last_heartbeat_publish_to_latch_s=(latch-last)/1e9,last_heartbeat_publish_to_zero_s=(zero-last)/1e9,observed_latch_zero_abs_gap_s=abs(zero-latch)/1e9,post_resume_nonzero=0,no_first_heartbeat_zero=True)
        receipt['injection_observed']=True
    stop()
    receipt['result']='PASS'
except BaseException as e:
    receipt['result']='FAIL';receipt['error']=repr(e);raise
finally:
    try:stop()
    finally:
        n.destroy_node();rclpy.try_shutdown()
        out.write_text(json.dumps(dict(receipt=receipt,trace=trace),indent=2,allow_nan=False)+'\n')
