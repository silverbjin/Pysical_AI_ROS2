import math,time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from geometry_msgs.msg import Twist,TwistStamped
from std_msgs.msg import Bool
from std_srvs.srv import Trigger
from ch15_interfaces.msg import ReadyState,SafetyState
from ch15_adapters.contracts import SafetyGate
from ch15_adapters.qos_profiles import profile,state_qos
class CommandArbiter(Node):
    def __init__(self):
        super().__init__('ch15_command_arbiter');self.gate=SafetyGate();self.ready=False;self.ready_at=0.;self.cmd=None;self.cmd_at=0.
        self.create_subscription(ReadyState,'/ch15/ready',self.on_ready,profile())
        self.create_subscription(Bool,'/ch15/stop_request',lambda m:self.gate.heartbeat(m.data,time.monotonic()),profile(10))
        self.create_subscription(TwistStamped,'/ch15/cmd_vel_in',self.on_command,profile())
        self.out=self.create_publisher(Twist,'/cmd_vel',profile())
        self.status=self.create_publisher(SafetyState,'/ch15/safety_state',state_qos)
        self.create_service(Trigger,'/ch15/reset_safety',self.reset)
        self.create_timer(.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def on_ready(self,msg):self.ready=msg.ready;self.ready_at=time.monotonic()
    def on_command(self,msg):self.cmd=msg;self.cmd_at=time.monotonic()
    def reset(self,req,res):
        res.success=False;res.message='G02: terminal/idle witness not installed; reset forbidden until G03/G08';return res
    def tick(self):
        now=time.monotonic();ready=self.ready and now-self.ready_at<=.3
        owner=self.count_publishers('/cmd_vel')==1 and self.count_publishers('/ch15/cmd_vel_in')==1 and self.count_publishers('/ch15/stop_request')==1
        blocked=self.gate.blocked(now,ready,owner);reason='gate' if blocked else ''
        out=Twist()
        if not blocked and self.cmd is not None:
            m=self.cmd;stamp=m.header.stamp.sec*1000000000+m.header.stamp.nanosec;age=self.get_clock().now().nanoseconds-stamp
            v=m.twist.linear;w=m.twist.angular
            valid=m.header.frame_id=='base_link' and stamp>0 and 0<=age<=500000000 and now-self.cmd_at<=.5 and all(math.isfinite(x) for x in (v.x,v.y,v.z,w.x,w.y,w.z))
            if valid:out=m.twist
            else:blocked=True;reason='invalid_or_stale_command'
        elif not blocked:blocked=True;reason='no_command'
        self.out.publish(out);s=SafetyState();s.header.stamp=self.get_clock().now().to_msg();s.epoch=0;s.blocked=blocked;s.latched=self.gate.latched;s.reason=reason;s.owner='MOCK:ch15_command_arbiter';self.status.publish(s)
def main():
    rclpy.init();node=CommandArbiter()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:node.out.publish(Twist());node.destroy_node();rclpy.try_shutdown()
