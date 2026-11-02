"""Synthetic DDS CPU attribution by OS thread; never engine/admission evidence.

Uses Python3.12 public sys.monitoring, avoiding cProfile's mismatched callback
thread-state accounting observed with the installed C++ EventsExecutor.
"""
import collections,hashlib,inspect,json,os,select,shutil,signal,subprocess,sys,threading,time,uuid
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='228';repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
import rclpy
from probe_navigation_13_5 import NavigationProbe,ProbeReceiver
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('probe-monitoring-'+str(uuid.uuid4()))
native.mkdir();shutil.copyfile(__file__,native/Path(__file__).name)
publisher_helper=Path(__file__).with_name('profile-probe-load.py')
shutil.copyfile(publisher_helper,native/publisher_helper.name)
monitor=sys.monitoring;tool=next(i for i in (3,4,2) if monitor.get_tool(i) is None)
events=monitor.events;monitor.use_tool_id(tool,'Ch13_synthetic_thread_CPU')
stacks={};costs={};selected={};mismatches=[]
prefixes=('/rclpy/','/probe_navigation_13_5.py','/g2_command_source.py','/dataclasses.py',
    '/json/','/geometry_msgs/','/nav_msgs/','/sensor_msgs/','/std_msgs/','/builtin_interfaces/',
    '/integrated_robot_navigation/')
def interested(code):
    if code not in selected:
        selected[code]=not code.co_flags&(inspect.CO_GENERATOR|inspect.CO_COROUTINE|inspect.CO_ASYNC_GENERATOR) and any(s in code.co_filename for s in prefixes)
    return selected[code]
def begin(code,offset):
    if not interested(code):return
    ident=threading.get_ident();now=time.thread_time_ns()
    stacks.setdefault(ident,[]).append([code,now,0])
def end(code,offset,value):
    if not interested(code):return
    ident=threading.get_ident();now=time.thread_time_ns();stack=stacks.get(ident,[])
    if not stack or stack[-1][0] is not code:
        mismatches.append((ident,code.co_name));return
    _,start,children=stack.pop();elapsed=now-start;exclusive=elapsed-children
    row=costs.setdefault((ident,code),[0,0,0]);row[0]+=1;row[1]+=exclusive;row[2]+=elapsed
    if stack:stack[-1][2]+=elapsed
monitor.register_callback(tool,events.PY_START,begin)
monitor.register_callback(tool,events.PY_RETURN,end)
monitor.register_callback(tool,events.PY_UNWIND,end)
peer=subprocess.Popen([sys.executable,str(publisher_helper),'publisher'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    text=True,start_new_session=True)
probe=receiver=None;failure=None;report={};started=None;cpu=None
try:
    if not select.select([peer.stdout],[],[],10.)[0] or peer.stdout.readline().strip()!='READY':raise RuntimeError('synthetic source not ready')
    rclpy.init();probe=NavigationProbe(native,engine='mujoco',bounded_history=True)
    monitor.set_events(tool,events.PY_START|events.PY_RETURN|events.PY_UNWIND)
    started=time.monotonic();cpu=time.process_time();receiver=ProbeReceiver(probe)
    time.sleep(5.);receiver.check()
except BaseException as error:failure=repr(error)
finally:
    try:
        if receiver is not None:
            joined=receiver.shutdown(timeout_sec=5.)
            report['receivers']=receiver.report()
            if not joined:raise RuntimeError('synthetic receivers not joined')
        if probe is not None:
            probe.close_log();report['timing']=probe.timing_snapshot();probe.destroy_node()
        if rclpy.ok():rclpy.try_shutdown()
    except BaseException as error:failure=failure or repr(error)
    monitor.set_events(tool,0)
    for event in (events.PY_START,events.PY_RETURN,events.PY_UNWIND):monitor.register_callback(tool,event,None)
    monitor.free_tool_id(tool)
    peer.send_signal(signal.SIGINT);stdout,stderr=peer.communicate(timeout=10.)
    if peer.returncode:failure=failure or ('publisher exit '+str(peer.returncode)+stderr)
rows=[dict(thread_ident=ident,file=code.co_filename,line=code.co_firstlineno,function=code.co_name,
    calls=value[0],self_cpu_s=value[1]/1e9,cumulative_cpu_s=value[2]/1e9) for (ident,code),value in costs.items()]
rows.sort(key=lambda r:-r['self_cpu_s'])
out=dict(scope='synthetic_sys_monitoring_per_OS_thread_CPU_not_engine_or_acceptance',
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),failure=failure,
    publisher_reaped=True,publisher_exit=peer.returncode,wall_s=time.monotonic()-started if started else None,
    process_cpu_s=time.process_time()-cpu if cpu is not None else None,
    stack_mismatches=mismatches,open_frames={str(k):len(v) for k,v in stacks.items()},rows=rows,**report)
with (native/'result.json').open('x') as output:json.dump(out,output,indent=2)
destination=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/native.name
shutil.copytree(native,destination)
for source in native.rglob('*'):
    if source.is_file():assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256((destination/source.relative_to(native)).read_bytes()).digest()
print(json.dumps(dict(output=str(destination),failure=failure,mismatches=len(mismatches),open_frames=out['open_frames'],
    wall_s=out['wall_s'],process_cpu_s=out['process_cpu_s'],top=rows[:12]),indent=2))
raise SystemExit(1 if failure or mismatches or any(stacks.values()) else 0)
