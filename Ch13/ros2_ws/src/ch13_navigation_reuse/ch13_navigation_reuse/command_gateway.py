"""ROS2 command ownership and safety boundary; no policy or actuator control."""
import argparse,json,math,time
from dataclasses import replace
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy._rclpy_pybind11 import RCLError
from rclpy.clock import Clock as TimerClock
from rclpy.clock_type import ClockType
from geometry_msgs.msg import TwistStamped
from rosgraph_msgs.msg import Clock
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from .safety import Guard
from .wire import decode
from .nav_contract import FutureInbox
from .startup_trace import StartupTrace
N='/ch13/reuse'
JOINT_NAMES=tuple(f'{leg}_{joint}_joint' for leg in ('FL','FR','RL','RR') for joint in ('hip','thigh','calf'))+tuple(f'joint{i}' for i in range(1,9))
def ns(stamp):return int(stamp.sec)*1_000_000_000+int(stamp.nanosec)
def gid(info):return bytes(info["publisher_gid"] if isinstance(info,dict) else info.publisher_gid).hex()
def set_stamp(stamp,value):stamp.sec=int(value)//1_000_000_000;stamp.nanosec=int(value)%1_000_000_000

def valid_command(msg):
    v,w=msg.twist.linear,msg.twist.angular;values=(v.x,v.y,v.z,w.x,w.y,w.z)
    return msg.header.frame_id=='reuse/nav_base' and all(math.isfinite(x) for x in values) and all(abs(values[i])<=1e-12 for i in [1,2,3,4])
def valid_base(msg):
    p=msg.pose.pose.position;q=msg.pose.pose.orientation;v=msg.twist.twist.linear;w=msg.twist.twist.angular
    return msg.header.frame_id=='reuse/odom' and msg.child_frame_id=='reuse/base' and all(math.isfinite(x) for x in [p.x,p.y,p.z,q.x,q.y,q.z,q.w,v.x,v.y,v.z,w.x,w.y,w.z]) and abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)<1e-3 and p.z>=.12 and 1-2*(q.x*q.x+q.y*q.y)>=math.cos(math.pi/4)
def valid_joints(msg,manipulation=False):
    if not (tuple(msg.name)==JOINT_NAMES and len(msg.position)==20 and len(msg.velocity)==20 and all(math.isfinite(x) for x in list(msg.position)+list(msg.velocity))):return False
    if not manipulation:return max(abs(x) for x in msg.position[12:18])<=.10
    limits=((-2.618,2.618),(0.,3.14),(-2.697,0.),(-1.832,1.832),(-1.22,1.22),(-3.14,3.14),(0.,.05),(-.05,0.))
    return all(lo-margin<=q<=hi+margin for q,(lo,hi),margin in zip(msg.position[12:],limits,[.02]*6+[.002]*2))

class CommandGateway(Node):
    def __init__(self,manipulation=False):
        self.manipulation=manipulation
        super().__init__('ch13_reuse_gateway');self.guard=Guard();self.pending=FutureInbox();self.previous_mode=None;self.safe_watermark_ns=0
        self.trace=StartupTrace.from_env('gateway')
        self.startup_sync=True
        if self.trace is not None:self.pending.audit=lambda *a:self.trace.inbox(*a,self.guard.clock_wall)
        self.safe=self.create_publisher(TwistStamped,N+'/cmd_vel_safe',1)
        self.status=self.create_publisher(String,N+'/gateway/status',1)
        self.create_subscription(String,N+'/ingress/gateway',self.on_packet,16)
        self.create_service(Trigger,N+'/gateway/arm',self.on_arm)
        self.create_service(Trigger,N+'/gateway/reset',self.on_reset)
        self.timer=self.create_timer(.02,self.tick,clock=TimerClock(clock_type=ClockType.STEADY_TIME))
    def dispatch(self,key,msg,info):
        {'raw':self.on_raw,'base':self.on_base,'joints':self.on_joints}[key](msg,info)
    def capture_fault(self):
        if self.trace is not None and self.guard.fault:self.trace.fault(self.guard.fault,self.pending.items,self.guard.clock_ns,self.guard.clock_wall,time.monotonic())
    def drain(self,now):
        try:
            for job in self.pending.ready(self.guard.clock_ns,now,clock_receipt=self.guard.clock_wall,startup=self.startup_sync):self.dispatch(*job)
        except ValueError:
            self.guard.trip('FUTURE_SOURCE:'+next(iter(self.pending.items),'unknown'))
            self.capture_fault()
    def on_packet(self,packet):
        try:
            key,msg,info=decode(packet.data)
            if self.trace is not None:self.trace.packet(key,ns(msg.clock) if key=='clock' else (ns(msg.header.stamp) if hasattr(msg,'header') else 0),info,time.monotonic(),self.guard.clock_ns,self.guard.clock_wall)
            if not self.guard._owner('relay',info['relay_gid']):return
            if key=='clock':self.on_clock(msg,info);self.drain(time.monotonic());return
            if key not in ('raw','base','joints'):raise ValueError('unexpected gateway channel')
            if not self.guard._owner(key,gid(info)):return
            if not {'raw':valid_command,'base':valid_base,'joints':lambda m:valid_joints(m,self.manipulation)}[key](msg):self.guard.trip('INVALID_COMMAND' if key=='raw' else 'INVALID_STATE:'+key);return
            if self.guard.clock_wall is None:return
            if ns(msg.header.stamp)-self.guard.clock_ns>100_000_000:self.guard.trip('FUTURE_SOURCE:'+key);self.capture_fault();return
            for job in self.pending.offer(key,ns(msg.header.stamp),info['receipt_wall'],(key,msg,info),self.guard.clock_ns,time.monotonic(),owner=gid(info),clock_receipt=self.guard.clock_wall,startup=self.startup_sync):self.dispatch(*job)
        except (ValueError,KeyError,TypeError) as exc:
            if self.pending.items:self.guard.trip('FUTURE_SOURCE:'+next(iter(self.pending.items)))
            else:self.guard.trip('INVALID_INGRESS:'+type(exc).__name__)
            self.capture_fault()
    def on_clock(self,msg,info):self.guard.clock(ns(msg.clock),info['receipt_wall'],gid(info))
    def on_base(self,msg,info):self.guard.observe('base',ns(msg.header.stamp),info['receipt_wall'],gid(info),valid_base(msg))
    def on_joints(self,msg,info):self.guard.observe('joints',ns(msg.header.stamp),info['receipt_wall'],gid(info),valid_joints(msg,self.manipulation))
    def on_raw(self,msg,info):
        v=msg.twist.linear;w=msg.twist.angular
        self.guard.command(ns(msg.header.stamp),info['receipt_wall'],gid(info),(v.x,v.y,v.z,w.x,w.y,w.z),msg.header.frame_id)
    def on_arm(self,request,response):
        response.success=not self.pending.items and self.guard.samples.get('raw',(0,))[0]>=self.safe_watermark_ns and self.guard.arm(time.monotonic())
        if response.success:self.startup_sync=False
        response.message=json.dumps({'mode':self.guard.mode,'fault':self.guard.fault,'counts':self.guard.counts,'observed':list(self.guard.samples)})
        return response
    def on_reset(self,request,response):
        self.guard.reset();self.pending=FutureInbox();self.startup_sync=True
        if self.trace is not None:self.pending.audit=lambda *a:self.trace.inbox(*a,self.guard.clock_wall)
        response.success=True;response.message='DISARMED: fresh zero input/state and explicit arm required';return response
    def tick(self):
        now=time.monotonic();self.drain(now)
        self.guard.graph({'clock':self.count_publishers('/clock'),'raw':self.count_publishers(N+'/cmd_vel_raw'),'base':self.count_publishers(N+'/engine_state'),'joints':self.count_publishers(N+'/joint_states'),'relay':self.count_publishers(N+'/ingress/gateway')},now)
        d=self.guard.output(now)
        self.capture_fault()
        if d.mode=='DISARMED':
            raw=self.guard.samples.get('raw');stamp=max(self.safe_watermark_ns,raw[0] if raw else d.stamp_ns)
            d=replace(d,stamp_ns=stamp) # zero only; freeze rather than launder an older native control stamp
        msg=TwistStamped();set_stamp(msg.header.stamp,d.stamp_ns);msg.header.frame_id='reuse/nav_base';msg.twist.linear.x=d.vx;msg.twist.angular.z=d.wz
        if d.stamp_ns>0:self.safe.publish(msg);self.safe_watermark_ns=max(self.safe_watermark_ns,d.stamp_ns)
        self.status.publish(String(data=json.dumps({'mode':d.mode,'fault':d.fault,'stamp_ns':d.stamp_ns,'clock_ns':self.guard.clock_ns,'origin':'source_command' if d.mode=='ARMED' else 'generated_safety_zero','decision_wall':now,'source_receipts':{k:{'stamp_ns':v[0],'receipt_wall':v[1],'gid':v[2]} for k,v in self.guard.samples.items()},'counts':self.guard.counts,'safe_watermark_ns':self.safe_watermark_ns,'pending_future_count':len(self.pending.items),'startup_sync':self.startup_sync,'ready_for_arm':not self.pending.items and self.guard.mode=='DISARMED' and self.guard._fresh(now) and self.guard.values==(0.,0.) and self.guard.samples.get('raw',(0,))[0]>=self.safe_watermark_ns})))
        if self.previous_mode!=d.mode:self.get_logger().info('mode='+d.mode+' '+d.fault);self.previous_mode=d.mode

def main(args=None):
    node=None
    parser=argparse.ArgumentParser();parser.add_argument('--manipulation',choices=['true','false'],default='false');options,ros_args=parser.parse_known_args(args)
    try:
        rclpy.init(args=ros_args);node=CommandGateway(options.manipulation=='true');rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException):pass
    except RCLError:
        # A signal can invalidate the context after a service becomes discoverable
        # but before construction finishes. Unrelated live-context errors still fail.
        if rclpy.ok():raise
    finally:
        if node is not None:
            node.destroy_node()
            if node.trace is not None:node.trace.write()
        rclpy.try_shutdown()
if __name__=='__main__':main()
