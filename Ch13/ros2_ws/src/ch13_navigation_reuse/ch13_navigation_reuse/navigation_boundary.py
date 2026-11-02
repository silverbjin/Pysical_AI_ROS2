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
from .nav_contract import NavigationContract
from .command_gateway import N,ns,set_stamp
from .wire import decode
class NavigationBoundary(Node):
 def __init__(self):
  super().__init__('ch13_reuse_navigation_boundary');self.c=NavigationContract();self.relay_gid=None
  self.raw=self.create_publisher(TwistStamped,N+'/cmd_vel_raw',1);self.status=self.create_publisher(String,N+'/navigation/status',1)
  self.create_subscription(String,N+'/ingress/navigation',self.packet,16)
  self.create_service(Trigger,N+'/navigation/enable',self.enable);self.create_service(Trigger,N+'/navigation/idle',self.idle);self.create_service(Trigger,N+'/navigation/reset',self.reset)
  self.create_timer(.02,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
 def packet(self,packet):
  try:
   key,m,i=decode(packet.data);gid=i['publisher_gid'].hex();wall=i['receipt_wall']
   if self.relay_gid is not None and self.relay_gid!=i['relay_gid']:self.c.trip('RELAY_REPLACED');return
   self.relay_gid=i['relay_gid']
   if key=='clock':self.c.clock(ns(m.clock),wall,gid)
   elif key in ('nav','smooth'):
    v,w=m.twist.linear,m.twist.angular;values=(v.x,v.y,v.z,w.x,w.y,w.z)
    if key=='nav':self.c.nav(ns(m.header.stamp),wall,gid,values,m.header.frame_id)
    else:self.c.smooth(ns(m.header.stamp),wall,gid,values)
   elif key=='scan':self.c.scan(ns(m.header.stamp),wall,gid,m.header.frame_id=='reuse/scan' and len(m.ranges)==181 and all(not math.isnan(x) and x>=0 for x in m.ranges))
   elif key in ('tf','tf_static'):
    for t in m.transforms:
     q=t.transform.rotation;p=t.transform.translation
     if not all(math.isfinite(x) for x in [q.x,q.y,q.z,q.w,p.x,p.y,p.z]) or abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)>.001:self.c.trip('INVALID_TF');return
     self.c.tf(t.header.frame_id,t.child_frame_id,ns(t.header.stamp),wall,gid)
  except (ValueError,KeyError,TypeError):self.c.trip('INVALID_NAV_INGRESS')
 def enable(self,request,response):response.success=self.c.enable(time.monotonic());response.message=self.c.phase;return response
 def idle(self,request,response):self.c.idle();response.success=self.c.phase=='IDLE';response.message=self.c.phase;return response
 def reset(self,request,response):self.c=NavigationContract();self.relay_gid=None;response.success=True;response.message='IDLE; fresh inputs/explicit enable required';return response
 def tick(self):
  now=time.monotonic();self.c.graph({'clock':self.count_publishers('/clock'),'nav':self.count_publishers(N+'/nav_cmd'),'smooth':self.count_publishers(N+'/smoothed_cmd'),'scan':self.count_publishers(N+'/scan'),'tf':1 if self.c.frames_ready() else 0},now)
  if self.count_publishers(N+'/cmd_vel_raw')!=1:self.c.trip('RAW_BYPASS')
  if self.count_publishers(N+'/ingress/navigation')>1:self.c.trip('DUPLICATE_RELAY')
  stamp,vx,wz,phase,fault=self.c.output(now)
  if stamp>0:
   m=TwistStamped();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/nav_base';m.twist.linear.x=vx;m.twist.angular.z=wz;self.raw.publish(m)
  self.status.publish(String(data=json.dumps({'phase':phase,'fault':fault,'stamp_ns':stamp,'vx':vx,'wz':wz,'origin':'controller_source_via_smoother' if phase=='ACTIVE' else 'generated_zero','frames_ready':self.c.frames_ready(),'samples':{k:{'stamp_ns':v[0],'receipt_wall':v[1],'gid':v[2]} for k,v in self.c.g.samples.items()}})))
def main():
 rclpy.init();node=NavigationBoundary()
 try:rclpy.spin(node)
 except (KeyboardInterrupt,ExternalShutdownException):pass
 finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
