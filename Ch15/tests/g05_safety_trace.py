"""Read-only observation of the original safety classes; no threshold or reset change."""
import json,sys,time
from pathlib import Path
import rclpy
from geometry_msgs.msg import Twist
from ch15_adapters.contracts import SafetyGate
from ch15_safety.command_arbiter import CommandArbiter
from ch15_safety.sensor_watchdog import SensorWatchdog
mode=sys.argv.pop(1);out=Path(sys.argv.pop(1));events=[]
def event(kind,**fields):events.append(dict(kind=kind,wall_ns=time.monotonic_ns(),**fields))
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
        super().tick()
        event('watchdog',age_s=age,source_stamp_ns=self.stamp,latched=self.latched,first_latch=not before and self.latched)
rclpy.init()
if mode=='arbiter':
    node=CommandArbiter()
    # No executor callbacks have run yet. Same initial SafetyGate values.
    node.gate=TracedGate()
elif mode=='watchdog':node=TracedWatchdog()
else:raise ValueError(mode)
try:rclpy.spin(node)
except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
finally:
    if mode=='arbiter' and rclpy.ok():node.out.publish(Twist())
    node.destroy_node();rclpy.try_shutdown()
    out.write_text(json.dumps(dict(mode=mode,events=events),indent=2)+'\n')
