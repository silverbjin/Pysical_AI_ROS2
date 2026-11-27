"""Actual DDS mock fixture only; G08 fault acceptance is separate."""
import sys,json,time
from pathlib import Path
import rclpy
from rclpy.executors import MultiThreadedExecutor
from ch15_adapters.mock_servers import MockServers
mode=sys.argv.pop(1);out=Path(sys.argv.pop(1));trace=[]
assert mode in ('normal','F01','F06')
def row(kind,**fields):trace.append(dict(kind=kind,wall_ns=time.monotonic_ns(),cpu_ns=time.thread_time_ns(),**fields))
class Fixture(MockServers):
    def on_ready(self,msg):
        super().on_ready(msg);row('ready_receipt',ready=msg.ready,stamp_ns=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec)
    def on_safety(self,msg):
        super().on_safety(msg);row('safety_receipt',latched=msg.latched,owner=msg.owner,stamp_ns=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec)
    def ready_now(self):
        now=time.monotonic();valid=super().ready_now();row('ready_gate',valid=valid,ready=self.ready,ready_age_s=now-self.ready_at,latched=self.safety_latched,safety_age_s=now-self.safety_at);return valid
    def admit(self,g,kind):
        result=super().admit(g,kind);row('goal_admission',action=kind,result=result.name,active=self.active);return result
    def command(self,x):
        super().command(x)
        if mode=='F01' and x>0:self.scan_enabled=False
    def execute(self,h,kind,action):
        if mode=='F06' and kind=='pick':
            result=action.Result();result.success=False;result.error_message='G05 F06 recording fixture: injected pick abort'
            h.abort()
            with self.lock:self.active=False
            return result
        return super().execute(h,kind,action)
rclpy.init();n=Fixture();ex=MultiThreadedExecutor(num_threads=4);ex.add_node(n)
try:ex.spin()
except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
finally:
    ex.shutdown(timeout_sec=6.);n.destroy_node();rclpy.try_shutdown()
    out.write_text(json.dumps(trace,indent=2)+'\n')
