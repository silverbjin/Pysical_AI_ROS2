"""Read-only timer benchmark of official Jazzy executor membership patterns."""
import json,os,time
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='138'
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
rows=[]
for membership in ('per_spin','persistent','per_spin','persistent'):
 context=Context();rclpy.init(context=context);node=rclpy.create_node('membership_cost_probe',context=context)
 executor=SingleThreadedExecutor(context=context);count=[0]
 timer=node.create_timer(.001,lambda:count.__setitem__(0,count[0]+1),clock=Clock(clock_type=ClockType.STEADY_TIME))
 if membership=='persistent':executor.add_node(node)
 start=time.monotonic();cpu=time.thread_time();spins=0
 try:
  while time.monotonic()-start<2.:
   if membership=='persistent':executor.spin_once(timeout_sec=.01)
   else:rclpy.spin_once(node,executor=executor,timeout_sec=.01)
   spins+=1
  rows.append(dict(membership=membership,wall_s=time.monotonic()-start,cpu_s=time.thread_time()-cpu,spins=spins,callbacks=count[0]))
 finally:
  executor.shutdown(timeout_sec=2.);node.destroy_node();context.try_shutdown()
result=dict(scope='isolated domain138 empty 1kHz timer; no message/physics/action/lease; not live CPU or stop-cause proof',rows=rows)
out=Path(__file__).parent/'executor_membership_cost_v50.json'
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
