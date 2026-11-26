import math,time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
from ch15_adapters.qos_profiles import sensor_qos,profile
class SensorWatchdog(Node):
    def __init__(self):
        super().__init__('ch15_sensor_watchdog');self.last=None;self.stamp=0;self.valid=False;self.latched=False
        self.create_subscription(LaserScan,'/scan',self.scan,sensor_qos)
        self.pub=self.create_publisher(Bool,'/ch15/stop_request',profile(10))
        self.create_timer(.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
    def scan(self,msg):
        self.last=time.monotonic();self.stamp=msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec
        self.valid=msg.header.frame_id=='base_link' and bool(msg.ranges) and all(math.isfinite(v) and msg.range_min<=v<=msg.range_max for v in msg.ranges)
    def tick(self):
        if self.last is None:return # no heartbeat => arbiter blocks startup
        age=self.get_clock().now().nanoseconds-self.stamp
        if not self.valid or time.monotonic()-self.last>1. or self.stamp<=0 or not 0<=age<=300000000:self.latched=True
        self.pub.publish(Bool(data=self.latched))
def main():
    rclpy.init();node=SensorWatchdog()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:node.destroy_node();rclpy.try_shutdown()
