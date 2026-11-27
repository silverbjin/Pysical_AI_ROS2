"""G05 isolated no-motion scan timing; original mock producer/guard, observer OFF/ON."""
import gc,json,os,sys,time,signal,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def write(path,rows):path.write_text(json.dumps(rows,indent=2)+'\n')
def now():return time.monotonic_ns()
def state():
    result={}
    for f in ('/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/cpu.stat','/sys/fs/cgroup/cpuset.cpus.effective','/proc/self/schedstat'):
        try:result[f]=Path(f).read_text().strip()
        except OSError:result[f]=None
    return result
def producer(out,kind,mode='normal'):
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import MultiThreadedExecutor,SingleThreadedExecutor
    from rclpy.clock import Clock,ClockType
    from sensor_msgs.msg import LaserScan
    from geometry_msgs.msg import TwistStamped
    from ch15_adapters.mock_servers import MockServers
    from ch15_adapters.qos_profiles import sensor_qos,profile
    rows=[];gc_rows=[]
    def event(k,**kw):rows.append(dict(kind=k,wall_ns=now(),thread_cpu_ns=time.thread_time_ns(),process_cpu_ns=time.process_time_ns(),**kw))
    def gc_cb(phase,info):gc_rows.append(dict(phase=phase,generation=info['generation'],wall_ns=now(),process_cpu_ns=time.process_time_ns()))
    gc.callbacks.append(gc_cb)
    class Timed:
        def __init__(self,p):self.p=p
        def publish(self,m):
            a=now();b=time.thread_time_ns();stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
            event('publish_enter',stamp_ns=stamp)
            try:return self.p.publish(m)
            finally:event('publish_exit',stamp_ns=stamp,wall_duration_ns=now()-a,cpu_duration_ns=time.thread_time_ns()-b)
        def __getattr__(self,k):return getattr(self.p,k)
    class Original(MockServers):
        def sample(self):
            a=now();b=time.thread_time_ns();event('sample_enter')
            try:super().sample()
            finally:event('sample_exit',wall_duration_ns=now()-a,cpu_duration_ns=time.thread_time_ns()-b)
    class Isolated(Node):
        def __init__(self):
            super().__init__('g05_scan_source')
            self.scan=Timed(self.create_publisher(LaserScan,'/scan',sensor_qos))
            self.enabled=True
            if mode=='F01':self.create_subscription(TwistStamped,'/ch15/cmd_vel_in',self.on_command,profile())
            self.create_timer(.1,self.sample,clock=Clock(clock_type=ClockType.STEADY_TIME))
        def on_command(self,m):
            if self.enabled and m.twist.linear.x>0:
                self.enabled=False;event('fault_injection',mode='F01',trigger='actual positive cmd_vel_in',command_stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec)
        def sample(self):
            if not self.enabled:return
            a=now();b=time.thread_time_ns();event('sample_enter')
            try:
                s=LaserScan();s.header.stamp=self.get_clock().now().to_msg();s.header.frame_id='base_link';s.angle_min=-.5;s.angle_max=.5;s.angle_increment=.5;s.range_min=.05;s.range_max=5.;s.ranges=[2.,2.,2.];self.scan.publish(s)
            finally:event('sample_exit',wall_duration_ns=now()-a,cpu_duration_ns=time.thread_time_ns()-b)
    rclpy.init(args=[]);start=state()
    n=Original() if kind=='original' else Isolated()
    if kind=='original':n.scan=Timed(n.scan)
    ex=MultiThreadedExecutor(num_threads=4) if kind=='original' else SingleThreadedExecutor()
    ex.add_node(n)
    try:ex.spin()
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        ex.shutdown(timeout_sec=6);n.destroy_node();rclpy.try_shutdown();gc.callbacks.remove(gc_cb)
        write(out,dict(kind=kind,mode=mode,affinity=sorted(os.sched_getaffinity(0)),start=start,end=state(),events=rows,gc=gc_rows))
def run_case(out,kind,record,domain):
    os.environ.update(ROS_DOMAIN_ID=str(domain),ROS_LOCALHOST_ONLY='1',ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST')
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import Bool
    from ch15_adapters.qos_profiles import sensor_qos,profile
    out.mkdir();cpus=sorted(os.sched_getaffinity(0));assert len(cpus)>=4
    children=[];scans=[];stops=[];exits=[];err=None;start=state();window=None
    def launch(name,cpu,args):
        log=(out/(name+'.log')).open('w');p=subprocess.Popen(['taskset','-c',cpu,*args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((name,p,log))
    rclpy.init(args=[]);n=Node('g05_scan_diag')
    n.create_subscription(LaserScan,'/scan',lambda m:scans.append(dict(wall_ns=now(),stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec)),sensor_qos)
    n.create_subscription(Bool,'/ch15/stop_request',lambda m:stops.append(dict(wall_ns=now(),stop=m.data)),profile(10))
    def until(pred,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if any(p.poll() is not None for _,p,_ in children):raise RuntimeError('child exited')
            rclpy.spin_once(n,timeout_sec=.02)
            if pred():return
        raise RuntimeError('deadline')
    try:
        if record:
            launch('recorder',str(cpus[-1]),['ros2','bag','record','--storage','mcap','--qos-profile-overrides-path',str(ROOT/'config/bag_qos.yaml'),'-o',str(out/'bag'),'--topics','/scan','/ch15/stop_request'])
            until(lambda:'rosbag2_recorder' in n.get_node_names(),10)
        launch('producer',','.join(map(str,cpus[1:-1])),[sys.executable,__file__,'producer',str(out/'producer.json'),kind])
        until(lambda:len(scans)>=6,10)
        launch('watchdog',str(cpus[0]),[sys.executable,str(ROOT/'tests/g05_safety_trace.py'),'watchdog',str(out/'watchdog.json')])
        until(lambda:len(stops)>=5 and (not record or all(any(x.node_name=='rosbag2_recorder' for x in n.get_subscriptions_info_by_topic(t)) for t in ('/scan','/ch15/stop_request'))),10)
        a=now();end=a+8_000_000_000;until(lambda:now()>=end,10);window=[a,now()]
    except Exception as e:err=repr(e)
    finally:
        for name,p,log in reversed(children):
            if p.poll() is None:p.send_signal(signal.SIGINT)
            forced=False
            try:rc=p.wait(timeout=8)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=3);forced=True
            exits.append(dict(name=name,exit=rc,forced=forced));log.close()
        n.destroy_node();rclpy.try_shutdown()
        write(out/'observer.json',dict(scans=scans,stops=stops,window=window,start=start,end=state(),exits=exits,error=err))
    if err:raise RuntimeError(err)
    p=json.loads((out/'producer.json').read_text());w=json.loads((out/'watchdog.json').read_text())['events']
    pubs=[r for r in p['events'] if r['kind']=='publish_enter'];ends=[r for r in p['events'] if r['kind']=='publish_exit'];samples=[r for r in p['events'] if r['kind']=='sample_enter']
    def gaps(rows,key):return [b[key]-a[key] for a,b in zip(rows,rows[1:])]
    # All source samples, including startup before measurement, and original guard first latch.
    latch=[r for r in w if r.get('first_latch')]
    rec=[r for r in w if r['kind']=='scan'];ticks=[r for r in w if r['kind']=='watchdog']
    result=dict(kind=kind,recorder=record,domain=domain,source_count=len(pubs),source_gap_ms=max(gaps(pubs,'stamp_ns'),default=0)/1e6,callback_gap_ms=max(gaps(samples,'wall_ns'),default=0)/1e6,publish_max_ms=max((r['wall_duration_ns'] for r in ends),default=0)/1e6,watchdog_receipt_gap_ms=max(gaps(rec,'wall_ns'),default=0)/1e6,watchdog_tick_gap_ms=max(gaps(ticks,'wall_ns'),default=0)/1e6,first_latch=latch[0] if latch else None,stop_true=sum(r['stop'] for r in stops),children=exits,window=window,source_stamps=len(set(r['stamp_ns'] for r in pubs)),motion_commands_sent=0)
    result['qualified']=len(pubs)>=70 and len(rec)>=70 and result['source_gap_ms']<=250 and result['watchdog_receipt_gap_ms']<=250 and result['watchdog_tick_gap_ms']<=100 and not latch and all(x['exit']==0 and not x['forced'] for x in exits)
    write(out/'result.json',result);print(json.dumps(result),flush=True);return result
if __name__=='__main__':
    if sys.argv[1]=='producer':producer(Path(sys.argv[2]),sys.argv[3],sys.argv[4] if len(sys.argv)>4 else 'normal')
    else:
        out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
        cases=[('isolated-on-cyclone','isolated',True,86)] if '--isolated-cyclone-qualify' in sys.argv else [('isolated-on-async','isolated',True,85)] if '--isolated-async-qualify' in sys.argv else [('original-on-async','original',True,84)] if '--async-qualify' in sys.argv else [('original-off','original',False,81),('original-on','original',True,82),('isolated-on','isolated',True,83)]
        results=[run_case(out/name,kind,on,d) for name,kind,on,d in cases]
        write(out/'diagnosis.json',dict(result='DIAGNOSTIC_COMPLETE',cases=results,original_source_unchanged=True,physical_motion=False,rmw=os.environ.get('RMW_IMPLEMENTATION'),publication_mode=os.environ.get('RMW_FASTRTPS_PUBLICATION_MODE')))
        if any(x in sys.argv for x in ('--async-qualify','--isolated-async-qualify','--isolated-cyclone-qualify')) and not all(r['qualified'] for r in results):raise SystemExit(1)
