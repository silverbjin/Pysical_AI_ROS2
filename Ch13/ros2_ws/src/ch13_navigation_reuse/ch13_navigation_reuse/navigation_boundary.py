"""Explicit Nav2 lease and TF-edge/scan audit before the existing gateway."""
import json,math,time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.executors import ExternalShutdownException
from std_msgs.msg import String
from std_srvs.srv import Trigger
from geometry_msgs.msg import TwistStamped
from .nav_contract import NavigationContract,FutureInbox
from .command_gateway import N,ns,set_stamp
from .wire import decode
from .vision_lease import VisionLease
class NavigationBoundary(Node):
 def __init__(self):
  super().__init__('ch13_reuse_navigation_boundary');self.c=NavigationContract();self.held=True;self.relay_gid=None;self.pending=FutureInbox();self.vision=VisionLease();self.vision_fault_record=None
  self.raw=self.create_publisher(TwistStamped,N+'/cmd_vel_raw',1);self.status=self.create_publisher(String,N+'/navigation/status',1)
  self.create_subscription(String,N+'/ingress/navigation',self.packet,16)
  self.create_service(Trigger,N+'/navigation/enable',self.enable);self.create_service(Trigger,N+'/navigation/release',self.release);self.create_service(Trigger,N+'/navigation/require_vision',self.require_vision);self.create_service(Trigger,N+'/navigation/idle',self.idle);self.create_service(Trigger,N+'/navigation/reset',self.reset)
  self.create_timer(.02,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
 def consume(self,key,m,i):
  gid=i['publisher_gid'].hex();wall=i['receipt_wall']
  if key=='vision_health':
   data=json.loads(m.data);capture=float(data['capture_wall'])
   if capture>i['receipt_wall']+.01:raise ValueError('vision capture after receipt')
   self.vision.observe(data['capture_ns'],capture,gid)
  elif key in ('nav','smooth'):
   v,w=m.twist.linear,m.twist.angular;values=(v.x,v.y,v.z,w.x,w.y,w.z)
   if key=='nav':self.c.nav(ns(m.header.stamp),wall,gid,values,m.header.frame_id)
   else:self.c.smooth(ns(m.header.stamp),wall,gid,values)
  elif key=='scan':self.c.scan(ns(m.header.stamp),wall,gid,m.header.frame_id=='reuse/scan' and len(m.ranges)==181 and all(not math.isnan(x) and x>=0 for x in m.ranges))
  elif key=='transform':
   q=m.transform.rotation;p=m.transform.translation
   if not all(math.isfinite(x) for x in [q.x,q.y,q.z,q.w,p.x,p.y,p.z]) or abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)>.001:self.c.trip('INVALID_TF');return
   self.c.tf(m.header.frame_id,m.child_frame_id,ns(m.header.stamp),wall,gid)
 def packet(self,packet):
  try:
   key,m,i=decode(packet.data)
   if self.relay_gid is not None and self.relay_gid!=i['relay_gid']:self.c.trip('RELAY_REPLACED');return
   self.relay_gid=i['relay_gid'];now=time.monotonic()
   if key=='clock':
    self.c.clock(ns(m.clock),i['receipt_wall'],i['publisher_gid'].hex())
    for job in self.pending.ready(self.c.g.clock_ns,now):self.consume(*job)
    return
   if key=='vision_health':self.consume(key,m,i);return
   jobs=[('transform',t,i) for t in m.transforms] if key in ('tf','tf_static') else [(key,m,i)]
   for kind,msg,info in jobs:
    if kind=='transform':
     previous=self.c.edges.get(msg.child_frame_id)
     if previous is not None and previous!=(msg.header.frame_id,info['publisher_gid'].hex()):self.c.trip('TF_EDGE_OWNER:'+msg.child_frame_id);return
    if self.c.g.clock_wall is None and ns(msg.header.stamp)>0:continue
    source=kind+(':'+msg.child_frame_id if kind=='transform' else '')
    for job in self.pending.offer(source,ns(msg.header.stamp),info['receipt_wall'],(kind,msg,info),self.c.g.clock_ns,now,owner=info['publisher_gid'].hex()):self.consume(*job)
  except (ValueError,KeyError,TypeError) as exc:self.c.trip('INVALID_NAV_INGRESS:'+str(exc))
 def require_vision(self,request,response):response.success=self.c.phase=='IDLE' and self.vision.enable(self.c.g.clock_ns,time.monotonic());response.message='vision lease required' if response.success else 'fresh original capture required';return response
 def enable(self,request,response):
  response.success=self.c.enable(time.monotonic())
  if response.success:self.held=True
  response.message=self.c.phase;return response
 def release(self,request,response):
  now=time.monotonic();response.success=self.held and self.c.phase=='ACTIVE' and self.c.g._fresh(now) and (not self.vision.active or self.vision.check(self.c.g.clock_ns,now))
  if response.success:self.held=False
  response.message='explicit release' if response.success else 'fresh prepared controller required';return response
 def idle(self,request,response):self.held=True;self.c.idle();response.success=self.c.phase=='IDLE';response.message=self.c.phase;return response
 def reset(self,request,response):self.c=NavigationContract();self.held=True;self.relay_gid=None;self.pending=FutureInbox();self.vision=VisionLease();self.vision_fault_record=None;response.success=True;response.message='IDLE; fresh inputs/explicit enable required';return response
 def tick(self):
  now=time.monotonic()
  try:
   for job in self.pending.ready(self.c.g.clock_ns,now):self.consume(*job)
  except ValueError as exc:self.c.trip('FUTURE_SOURCE_TIMEOUT:'+str(exc))
  self.c.graph({'clock':self.count_publishers('/clock'),'nav':self.count_publishers(N+'/nav_cmd'),'smooth':self.count_publishers(N+'/smoothed_cmd'),'scan':self.count_publishers(N+'/scan'),'tf':1 if self.c.frames_ready() else 0},now)
  if self.count_publishers(N+'/cmd_vel_raw')!=1:self.c.trip('RAW_BYPASS')
  if self.count_publishers(N+'/ingress/navigation')>1:self.c.trip('DUPLICATE_RELAY')
  if self.vision.active and self.c.phase in ('WAITING','ACTIVE'):
   if not self.vision.check(self.c.g.clock_ns,now) or self.count_publishers(N+'/vision/health')!=1:
    if self.vision_fault_record is None:self.vision_fault_record={'decision_wall':now,'clock_ns':self.c.g.clock_ns,'sample':self.vision.sample,'fault':self.vision.fault or 'VISION_OWNER_COUNT'}
    self.c.trip(self.vision.fault or 'VISION_OWNER_COUNT')
  stamp,vx,wz,phase,fault=self.c.output(now)
  if self.held:vx=wz=0.
  if stamp>0:
   m=TwistStamped();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/nav_base';m.twist.linear.x=vx;m.twist.angular.z=wz;self.raw.publish(m)
  self.status.publish(String(data=json.dumps({'phase':phase,'fault':fault,'stamp_ns':stamp,'vx':vx,'wz':wz,'output_held':self.held,'origin':('held_zero_with_controller_stamp' if self.held else 'controller_source_via_smoother') if phase=='ACTIVE' else 'generated_zero','frames_ready':self.c.frames_ready(),'vision_capture_ns':0 if self.vision.sample is None else self.vision.sample[0],'vision_capture_age_wall_s':None if self.vision.sample is None else now-self.vision.sample[1],'vision_fault_record':self.vision_fault_record,'samples':{k:{'stamp_ns':v[0],'receipt_wall':v[1],'gid':v[2]} for k,v in self.c.g.samples.items()}})))
def main():
 rclpy.init();node=NavigationBoundary()
 try:rclpy.spin(node)
 except (KeyboardInterrupt,ExternalShutdownException):pass
 finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
