"""Original MissionExecutor with observation only; no admission or safety semantics changed."""
import sys,json,time
from pathlib import Path
import rclpy
from ch15_mission.mission_executor import MissionExecutor
out=Path(sys.argv.pop(1));rows=[]
def row(kind,**fields):rows.append(dict(kind=kind,wall_ns=time.monotonic_ns(),cpu_ns=time.thread_time_ns(),**fields))
class TracedExecutor(MissionExecutor):
    def on_ready(self,m):
        super().on_ready(m);row('ready_receipt',ready=m.ready,missing=list(m.missing),count=self.ready_count,stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec)
    def on_safety(self,m):
        super().on_safety(m);row('safety_receipt',latched=m.latched,blocked=m.blocked,owner=m.owner,stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec)
    def fresh_ready(self):
        now=time.monotonic();ok=super().fresh_ready()
        row('fresh_ready',ok=ok,ready_count=self.ready_count,ready_age_s=now-self.ready_at,safety_age_s=now-self.safe_at,safety_latched=self.safety.latched if self.safety is not None else None,safety_owner=self.safety.owner if self.safety is not None else None)
        return ok
    def begin(self):
        row('begin_enter',started=self.started,finished=self.finished,all_terminal=self.all_terminal())
        result=super().begin();row('begin_result',success=result);return result
    def tick(self):
        a=time.monotonic_ns();c=time.thread_time_ns()
        try:super().tick()
        finally:row('tick_exit',duration_ns=time.monotonic_ns()-a,cpu_duration_ns=time.thread_time_ns()-c)
rclpy.init();n=TracedExecutor()
try:rclpy.spin(n)
except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
finally:
    clean=n.all_terminal() and (not n.started or n.finished)
    n.close();n.destroy_node();rclpy.try_shutdown();out.write_text(json.dumps(rows,indent=2)+'\n')
if not clean:raise SystemExit(2)
