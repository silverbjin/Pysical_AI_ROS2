"""ROS2 command ownership and safety boundary; no policy or actuator control."""
import json,math,time
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
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
N='/ch13/reuse'
JOINT_NAMES=tuple(f'{leg}_{joint}_joint' for leg in ('FL','FR','RL','RR') for joint in ('hip','thigh','calf'))+tuple(f'joint{i}' for i in range(1,9))
def ns(stamp):return int(stamp.sec)*1_000_000_000+int(stamp.nanosec)
def gid(info):return bytes(info["publisher_gid"] if isinstance(info,dict) else info.publisher_gid).hex()
def set_stamp(stamp,value):stamp.sec=int(value)//1_000_000_000;stamp.nanosec=int(value)%1_000_000_000

class CommandGateway(Node):
    def __init__(self):
        super().__init__('ch13_reuse_gateway');self.guard=Guard();self.previous_mode=None
        self.safe=self.create_publisher(TwistStamped,N+'/cmd_vel_safe',1)
        self.status=self.create_publisher(String,N+'/gateway/status',1)
        self.create_subscription(String,N+'/ingress/gateway',self.on_packet,16)
        self.create_service(Trigger,N+'/gateway/arm',self.on_arm)
        self.create_service(Trigger,N+'/gateway/reset',self.on_reset)
        self.timer=self.create_timer(.02,self.tick,clock=TimerClock(clock_type=ClockType.STEADY_TIME))
    def on_packet(self,packet):
        try:
            key,msg,info=decode(packet.data)
            if not self.guard._owner('relay',info['relay_gid']):return
            {'clock':self.on_clock,'raw':self.on_raw,'base':self.on_base,'joints':self.on_joints}[key](msg,info)
        except (ValueError,KeyError,TypeError) as exc:self.guard.trip('INVALID_INGRESS:'+type(exc).__name__)
    def on_clock(self,msg,info):self.guard.clock(ns(msg.clock),info['receipt_wall'],gid(info))
    def on_base(self,msg,info):
        p=msg.pose.pose.position;q=msg.pose.pose.orientation;v=msg.twist.twist.linear;w=msg.twist.twist.angular
        valid=msg.header.frame_id=='reuse/odom' and msg.child_frame_id=='reuse/base' and all(math.isfinite(x) for x in [p.x,p.y,p.z,q.x,q.y,q.z,q.w,v.x,v.y,v.z,w.x,w.y,w.z])
        valid=valid and abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)<1e-3 and p.z>=.12 and 1-2*(q.x*q.x+q.y*q.y)>=math.cos(math.pi/4)
        self.guard.observe('base',ns(msg.header.stamp),info['receipt_wall'],gid(info),valid)
    def on_joints(self,msg,info):
        valid=tuple(msg.name)==JOINT_NAMES and len(msg.position)==20 and len(msg.velocity)==20
        valid=valid and all(math.isfinite(x) for x in list(msg.position)+list(msg.velocity)) and max(abs(x) for x in msg.position[12:18])<=.10
        self.guard.observe('joints',ns(msg.header.stamp),info['receipt_wall'],gid(info),valid)
    def on_raw(self,msg,info):
        v=msg.twist.linear;w=msg.twist.angular
        self.guard.command(ns(msg.header.stamp),info['receipt_wall'],gid(info),(v.x,v.y,v.z,w.x,w.y,w.z),msg.header.frame_id)
    def on_arm(self,request,response):
        response.success=self.guard.arm(time.monotonic());response.message=json.dumps({'mode':self.guard.mode,'fault':self.guard.fault,'counts':self.guard.counts,'observed':list(self.guard.samples)})
        return response
    def on_reset(self,request,response):
        self.guard.reset();response.success=True;response.message='DISARMED: fresh zero input/state and explicit arm required';return response
    def tick(self):
        now=time.monotonic()
        self.guard.graph({'clock':self.count_publishers('/clock'),'raw':self.count_publishers(N+'/cmd_vel_raw'),'base':self.count_publishers(N+'/engine_state'),'joints':self.count_publishers(N+'/joint_states'),'relay':self.count_publishers(N+'/ingress/gateway')},now)
        d=self.guard.output(now);msg=TwistStamped();set_stamp(msg.header.stamp,d.stamp_ns);msg.header.frame_id='reuse/nav_base';msg.twist.linear.x=d.vx;msg.twist.angular.z=d.wz
        if d.stamp_ns>0:self.safe.publish(msg)
        self.status.publish(String(data=json.dumps({'mode':d.mode,'fault':d.fault,'stamp_ns':d.stamp_ns,'clock_ns':self.guard.clock_ns,'origin':'source_command' if d.mode=='ARMED' else 'generated_safety_zero','decision_wall':now,'source_receipts':{k:{'stamp_ns':v[0],'receipt_wall':v[1],'gid':v[2]} for k,v in self.guard.samples.items()},'counts':self.guard.counts,'ready_for_arm':self.guard.mode=='DISARMED' and self.guard._fresh(now) and self.guard.values==(0.,0.)})))
        if self.previous_mode!=d.mode:self.get_logger().info('mode='+d.mode+' '+d.fault);self.previous_mode=d.mode

def main(args=None):
    rclpy.init(args=args);node=CommandGateway()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException):pass
    finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
