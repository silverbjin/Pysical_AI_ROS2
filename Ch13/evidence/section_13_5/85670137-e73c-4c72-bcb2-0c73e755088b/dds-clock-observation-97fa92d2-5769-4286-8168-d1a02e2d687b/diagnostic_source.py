"""Clock/DDS-only diagnostic: isolated topics, no engine, TF or motor commands."""
import hashlib,json,os,subprocess,sys,time,uuid
from pathlib import Path

def clock_sample():
 a=time.monotonic_ns();s=time.time_ns();b=time.monotonic_ns()
 return dict(wall_ns=(a+b)//2,system_ns=s,span_ns=b-a,offset_ns=s-(a+b)//2)

if len(sys.argv)>1 and sys.argv[1]=='--role':
 role=sys.argv[2];root=Path(sys.argv[3]);duration=float(sys.argv[4])
 import rclpy
 from rclpy.context import Context
 from rclpy.node import Node
 from rclpy.clock import Clock
 from rclpy.clock_type import ClockType
 from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
 from rclpy.qos import QoSProfile,ReliabilityPolicy
 from std_msgs.msg import UInt64
 from integrated_robot_runtime.common import DrainingExecutor
 ctx=Context();rclpy.init(context=ctx);node=Node('clock_diagnostic_'+role,context=ctx)
 rows=[];last=[None];qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE)
 topic='/clock_diagnostic/'+root.name.replace('-','_')
 steady=Clock(clock_type=ClockType.STEADY_TIME)
 if role=='publisher':
  pub=node.create_publisher(UInt64,topic,qos)
  def send():
   now=clock_sample();pub.publish(UInt64(data=now['wall_ns']));rows.append(dict(kind='published',**now))
  node.create_timer(.02,send,clock=steady)
 else:
  group=MutuallyExclusiveCallbackGroup()
  def receive(msg,info):
   now=clock_sample();last[0]=msg.data
   # Jazzy RMW callback metadata is a dict in this installed rclpy.
   def field(name):return info.get(name) if isinstance(info,dict) else getattr(info,name,None)
   rows.append(dict(kind='received',capture_wall_ns=msg.data,source_system_ns=field('source_timestamp'),
    rmw_system_ns=field('received_timestamp'),**now))
  node.create_subscription(UInt64,topic,receive,qos,callback_group=group)
  def decision():
   now=clock_sample();rows.append(dict(kind='decision',selected_capture_wall_ns=last[0],**now))
  node.create_timer(.02,decision,clock=steady)
 executor=DrainingExecutor(num_threads=2,context=ctx);executor.add_node(node)
 (root/(role+'-ready.json')).write_text(json.dumps(dict(pid=os.getpid(),uid=os.getuid(),clock=clock_sample())))
 end=time.monotonic()+duration
 while time.monotonic()<end:executor.spin_once(timeout_sec=.002)
 joined=executor.shutdown(timeout_sec=2.);node.destroy_node();ctx.try_shutdown()
 (root/(role+'.json')).write_text(json.dumps(dict(rows=rows,executor_joined=joined,normal_exit=joined is not False)))
 raise SystemExit(0 if joined is not False else 1)

base=Path(sys.argv[1]);root=base/('dds-clock-observation-'+str(uuid.uuid4()));root.mkdir()
(root/'diagnostic_source.py').write_bytes(Path(__file__).read_bytes())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
start=dict(boot_id=boot,uid=os.getuid(),pid=os.getpid(),uptime=Path('/proc/uptime').read_text().strip(),
 command=sys.argv,ros_domain_id=os.environ.get('ROS_DOMAIN_ID'),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'start.json').write_text(json.dumps(start,indent=2));print(json.dumps(dict(path=str(root),**start)),flush=True)
logs=[];processes=[];clock=[]
def launch(role,duration):
 log=(root/(role+'.log')).open('x');logs.append(log)
 p=subprocess.Popen([sys.executable,__file__,'--role',role,str(root),str(duration)],stdout=log,stderr=subprocess.STDOUT);processes.append(p);return p
receiver=launch('receiver',88.);until=time.monotonic()+15.
while not (root/'receiver-ready.json').exists() and time.monotonic()<until:
 clock.append(clock_sample());time.sleep(.01)
assert (root/'receiver-ready.json').exists(),'receiver readiness missing; no retry/engine'
publisher=launch('publisher',80.);until=time.monotonic()+105.
while any(p.poll() is None for p in processes) and time.monotonic()<until:
 clock.append(clock_sample());time.sleep(.01)
assert all(p.poll() is not None for p in processes),'owned diagnostic still live; next engine forbidden'
for log in logs:log.close()
(root/'clock.json').write_text(json.dumps(clock))
jumps=[dict(wall_ns=b['wall_ns'],offset_delta_ns=b['offset_ns']-a['offset_ns']) for a,b in zip(clock,clock[1:]) if abs(b['offset_ns']-a['offset_ns'])>1_000_000]
received=json.loads((root/'receiver.json').read_text());pub=json.loads((root/'publisher.json').read_text())
r=[v for v in received['rows'] if v['kind']=='received'];p=pub['rows']
report=dict(scope='synthetic_DDS_clock_diagnostic_not_engine_acceptance',same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 returncodes=[v.returncode for v in processes],clock_jumps=jumps,published=len(p),received=len(r),
 maximum_publisher_gap_ms=max((b['wall_ns']-a['wall_ns'])/1e6 for a,b in zip(p,p[1:])),
 maximum_callback_gap_ms=max((b['wall_ns']-a['wall_ns'])/1e6 for a,b in zip(r,r[1:])),
 maximum_capture_age_ms=max((v['wall_ns']-v['capture_wall_ns'])/1e6 for v in r),
 receiver_joined=received['executor_joined'],publisher_joined=pub['executor_joined'])
(root/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
