import math,time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.clock import Clock,ClockType
from rclpy.time import Time
from tf2_ros import Buffer,TransformListener
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from ch15_interfaces.action import PickObject,PlaceObject
from ch15_interfaces.srv import SwitchGait
from ch15_interfaces.msg import ReadyState
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
from ch15_adapters.contracts import ReadinessGate
from ch15_adapters.qos_profiles import profile,sensor_qos
def stamp_ns(s):return int(s.sec)*1000000000+int(s.nanosec)
class ReadinessMonitor(Node):
    def __init__(self):
        super().__init__('ch15_readiness_monitor')
        self.gate=ReadinessGate();self.scan_at=None;self.scan_stamp=0;self.stop_at=None;self.stop=True
        self.actions=[ActionClient(self,a,n) for a,n in [(NavigateToPose,'/navigate_to_pose'),(PickObject,'/pick_object'),(PlaceObject,'/place_object')]]
        self.gait=self.create_client(SwitchGait,'/switch_gait')
        self.lifecycle_name=self.declare_parameter('required_lifecycle_node','').value
        self.lifecycle=self.create_client(GetState,self.lifecycle_name+'/get_state') if self.lifecycle_name else None
        self.life_future=None;self.life_at=None;self.life_active=False
        self.tf=Buffer();self.listener=TransformListener(self.tf,self)
        self.create_subscription(LaserScan,'/scan',self.scan,sensor_qos)
        self.create_subscription(Bool,'/ch15/stop_request',self.heartbeat,profile(10))
        self.pub=self.create_publisher(ReadyState,'/ch15/ready',profile())
        self.create_timer(.1,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def scan(self,msg):
        if msg.header.frame_id=='base_link' and msg.ranges and all(math.isfinite(x) and msg.range_min<=x<=msg.range_max for x in msg.ranges):
            self.scan_at=time.monotonic();self.scan_stamp=stamp_ns(msg.header.stamp)
        else:self.scan_at=None
    def heartbeat(self,msg):self.stop_at=time.monotonic();self.stop=msg.data
    def tick(self):
        now=time.monotonic();ros=self.get_clock().now().nanoseconds;missing=[]
        if not all(c.server_is_ready() for c in self.actions) or not self.gait.service_is_ready():missing.append('server')
        if self.scan_at is None or now-self.scan_at>.3 or not 0<self.scan_stamp<=ros or ros-self.scan_stamp>300000000:missing.append('sensor')
        if self.stop_at is None or now-self.stop_at>.15 or self.stop:missing.append('heartbeat')
        if not self.tf.can_transform('map','base_link',Time()):missing.append('tf')
        if self.count_publishers('/cmd_vel')!=1 or self.count_publishers('/ch15/cmd_vel_in')!=1 or self.count_publishers('/ch15/stop_request')!=1:missing.append('owner')
        if self.lifecycle:
            if self.life_future is not None and self.life_future.done():
                try:self.life_active=self.life_future.result().current_state.id==3;self.life_at=now
                except Exception:self.life_active=False
                self.life_future=None
            if self.life_future is None and self.lifecycle.service_is_ready():self.life_future=self.lifecycle.call_async(GetState.Request())
            if not self.life_active or self.life_at is None or now-self.life_at>.3:missing.append('lifecycle')
        m=ReadyState();m.header.stamp=self.get_clock().now().to_msg();m.epoch=0;m.ready=self.gate.sample(missing);m.missing=missing;self.pub.publish(m)
def main():
    rclpy.init();node=ReadinessMonitor()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:node.destroy_node();rclpy.try_shutdown()
