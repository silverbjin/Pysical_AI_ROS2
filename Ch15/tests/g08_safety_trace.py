"""Read-only observation of the original safety classes; no threshold or reset change."""
import json,sys,time
from pathlib import Path
import rclpy
from geometry_msgs.msg import Twist
from ch15_adapters.contracts import SafetyGate
from ch15_safety.command_arbiter import CommandArbiter
from ch15_safety.sensor_watchdog import SensorWatchdog
mode=sys.argv.pop(1);out=Path(sys.argv.pop(1));events=[]
def event(kind,**fields):events.append(dict(kind=kind,wall_ns=time.monotonic_ns(),cpu_ns=time.thread_time_ns(),**fields))
class TimedPublisher:
    def __init__(self,pub,name):self.pub=pub;self.name=name
    def publish(self,m):
        start=time.monotonic_ns();cpu=time.thread_time_ns()
        try:return self.pub.publish(m)
        finally:
            detail={}
            if self.name=='/cmd_vel':
                detail['zero']=all(v==0. for v in (m.linear.x,m.linear.y,m.linear.z,m.angular.x,m.angular.y,m.angular.z))
                detail['vx']=m.linear.x
            event('publish',topic=self.name,wall_duration_ns=time.monotonic_ns()-start,cpu_duration_ns=time.thread_time_ns()-cpu,publish_enter_ns=start,**detail)
    def __getattr__(self,name):return getattr(self.pub,name)
class TracedArbiter(CommandArbiter):
    def tick(self):
        start=time.monotonic_ns();cpu=time.thread_time_ns()
        event('tick_enter')
        try:super().tick()
        finally:event('tick_exit',wall_duration_ns=time.monotonic_ns()-start,cpu_duration_ns=time.thread_time_ns()-cpu)

class TracedGate(SafetyGate):
    def heartbeat(self,stop,now):
        before=self.latched;gap=None if self.last is None else now-self.last
        super().heartbeat(stop,now)
        event('heartbeat',stop=stop,gap_s=gap,latched=self.latched,first_latch=not before and self.latched)
    def blocked(self,now,ready,owner):
        before=self.latched;gap=None if self.last is None else now-self.last
        value=super().blocked(now,ready,owner)
        event('blocked',ready=ready,owner=owner,gap_s=gap,stop=self.stop,latched=self.latched,first_latch=not before and self.latched,value=value)
        return value
class TracedWatchdog(SensorWatchdog):
    def scan(self,msg):
        super().scan(msg);event('scan',stamp_ns=self.stamp,valid=self.valid)
    def tick(self):
        before=self.latched;age=None if self.last is None else time.monotonic()-self.last
        start=time.monotonic_ns();cpu=time.thread_time_ns()
        event('watchdog_enter',age_s=age,source_stamp_ns=self.stamp)
        super().tick()
        event('watchdog',age_s=age,source_stamp_ns=self.stamp,latched=self.latched,first_latch=not before and self.latched,wall_duration_ns=time.monotonic_ns()-start,cpu_duration_ns=time.thread_time_ns()-cpu)
rclpy.init()
if mode=='arbiter':
    node=TracedArbiter()
    node.out=TimedPublisher(node.out,'/cmd_vel')
    node.status=TimedPublisher(node.status,'/ch15/safety_state')
    # No executor callbacks have run yet. Same initial SafetyGate values.
    node.gate=TracedGate()
elif mode=='watchdog':
    node=TracedWatchdog();node.pub=TimedPublisher(node.pub,'/ch15/stop_request')
else:raise ValueError(mode)
try:rclpy.spin(node)
except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
finally:
    if mode=='arbiter' and rclpy.ok():node.out.publish(Twist())
    node.destroy_node();rclpy.try_shutdown()
    out.write_text(json.dumps(dict(mode=mode,events=events),indent=2)+'\n')
