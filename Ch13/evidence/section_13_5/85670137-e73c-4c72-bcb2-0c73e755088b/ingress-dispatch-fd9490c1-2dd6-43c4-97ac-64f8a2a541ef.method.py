"""Synthetic DDS ingress comparison, no engine, model or command publisher.

The two existing installed executors receive the same six observation types
and clock. This measures receiver cost, not native physics or acceptance.
"""
import json,os,sys,time,uuid,threading
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState,Imu,LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point,Vector3
from rosgraph_msgs.msg import Clock
from integrated_robot_interfaces.msg import FootContacts,MotionState
from integrated_robot_navigation.ingress_dispatch import IngressDispatch
from integrated_robot_navigation.observations import sensor_sample,SensorInbox
from integrated_robot_navigation.dispatch_node import event_backend_manifest

base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
out=dict(scope='synthetic_dds_only_no_engine_or_motion_acceptance',pid=os.getpid(),
 dependency_manifest=event_backend_manifest(),trials=[])
for index,backend in enumerate(('waitset','events','events','waitset')):
 ctx=Context();rclpy.init(context=ctx);peer=Node('bounded_ingress_source',context=ctx)
 inbox=SensorInbox(0);lock=threading.Lock();counts={};original={};latencies=[]
 messages=dict(joints=JointState(name=['a','b','c'],position=[0.]*3,velocity=[0.]*3),
  imu=Imu(),body=Odometry(child_frame_id='base_footprint'),
  scan=LaserScan(range_min=.05,range_max=5.,ranges=[1.]*120),
  carry=MotionState(ready=True),contacts=FootContacts(epoch=0,names=['fr_foot','fl_foot','rr_foot','rl_foot'],
   points=[Point() for _ in range(4)],normal_forces=[35.]*4,touching=[True]*4,
   forces_world=[Vector3(z=35.) for _ in range(4)],force_vectors_valid=True),clock=Clock())
 messages['body'].header.frame_id='odom';messages['body'].pose.pose.orientation.w=1.
 messages['imu'].header.frame_id='base_link';messages['contacts'].header.frame_id='odom'
 subscriptions=[];pubs={};sent={k:0 for k in messages};received={k:[] for k in messages}
 for key,msg in messages.items():
  def receive(message,key=key):
   receipt=time.monotonic_ns();stamp=message.clock if key=='clock' else message.header.stamp
   capture=stamp.sec*10**9+stamp.nanosec
   with lock:
    received[key].append(capture)
    started=original.get((key,capture))
    if started is not None:latencies.append(receipt-started)
    if key!='clock':inbox.receive(key,sensor_sample(key,message,receipt,0))
  topic='/ingress_comparison_'+str(index)+'/'+key
  subscriptions.append(((type(msg),topic,receive,qos_profile_sensor_data),{}))
  pubs[key]=peer.create_publisher(type(msg),topic,qos_profile_sensor_data)
 worker=IngressDispatch(ctx,'bounded_ingress_receiver','/',subscriptions,autostart=False)
 try:
  worker.select_backend(backend);worker.start();deadline=time.monotonic()+3.
  while not all(p.get_subscription_count()==1 for p in pubs.values()) and time.monotonic()<deadline:time.sleep(.005)
  if not all(p.get_subscription_count()==1 for p in pubs.values()):raise RuntimeError('DDS comparison discovery incomplete')
  start=time.monotonic_ns();cpu=time.process_time_ns();rates=dict(clock=100,joints=100,imu=100,body=50,contacts=50,carry=50,scan=10)
  duration=4.;deadline=start+int(duration*1e9)
  while (now:=time.monotonic_ns())<deadline:
   for key,msg in messages.items():
    if (now-start)*rates[key]//10**9>=sent[key]:
     seq=sent[key]+1;stamp=msg.clock if key=='clock' else msg.header.stamp
     stamp.sec=seq//1000;stamp.nanosec=(seq%1000)*1000000
     capture=stamp.sec*10**9+stamp.nanosec
     with lock:original[(key,capture)]=time.monotonic_ns()
     pubs[key].publish(msg);sent[key]+=1
   time.sleep(.0005)
  elapsed=time.monotonic_ns()-start;cpu_used=time.process_time_ns()-cpu
  time.sleep(.1)
  if worker.error:raise RuntimeError(worker.error)
  with lock:
   report=dict(backend=backend,wall_ns=elapsed,process_cpu_ns=cpu_used,cpu_cores=cpu_used/elapsed,
    sent=sent,received={k:len(v) for k,v in received.items()},
    strictly_increasing={k:all(a<b for a,b in zip(v,v[1:])) for k,v in received.items()},
    latency_max_ns=max(latencies),latency_p99_ns=sorted(latencies)[int(.99*(len(latencies)-1))],
    pending_max=max(map(len,inbox.pending.values())))
 finally:
  worker.close();peer.destroy_node();ctx.try_shutdown()
 report.update(joined=worker.joined,thread_alive=worker.thread.is_alive(),error=worker.error)
 out['trials'].append(report)
target=base/('ingress-dispatch-'+str(uuid.uuid4())+'.json')
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),trials=out['trials']),indent=2))
