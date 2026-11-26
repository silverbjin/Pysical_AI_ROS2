"""Independent replay witness with signal-controlled evidence persistence."""
import argparse,json,signal,time,math,tempfile,os
from pathlib import Path
import rclpy
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import PointStamped
from ch14_performance_monitor.monitor_node import Monitor,ns
class Witness(Monitor):
    def __init__(self):
        super().__init__();self.points=[];self.clock_counts=[];self.independent_age=[]
        self.create_subscription(PointStamped,"/perception/target_point",self.point,10)
    def point(self,m):self.points.append(dict(stamp=ns(m.header),frame=m.header.frame_id,xyz=[m.point.x,m.point.y,m.point.z]))
    def clock(self,m):
        super().clock(m);self.clock_counts.append(self.count_publishers("/clock"))
    def det(self,m):
        super().det(m)
        if self.clocks:self.independent_age.append(dict(stamp=ns(m.header),clock_ns=self.clocks[-1][0],observed_age_ms=(self.clocks[-1][0]-ns(m.header))/1e6))
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);p.add_argument("--timeout",type=float,default=45.);a=p.parse_args()
    # Check real bind-mount write access before discovery, with no permission escalation.
    if a.out.exists():raise FileExistsError(str(a.out))
    with tempfile.NamedTemporaryFile(dir=a.out.parent,prefix=".ch14-write-probe-") as f:
        f.write(b"ok");f.flush()
    print(json.dumps(dict(status="EVIDENCE_WRITABLE",uid=os.getuid(),gid=os.getgid())),flush=True)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO);w=Witness();stop=False
    def handler(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGINT,handler);signal.signal(signal.SIGTERM,handler)
    end=time.monotonic()+a.timeout
    try:
        while not stop and time.monotonic()<end:w.spin(.05)
    finally:
        data=w.snapshot();hits={x["stamp"] for x in w.outputs if any(b["label"]=="bus" and b["score"]>=.5 for b in x["boxes"])}
        points={p["stamp"] for p in w.points if p["frame"]=="odom" and all(math.isfinite(v) for v in p["xyz"]) and abs(p["xyz"][2]-2.)<1e-5}
        matched=hits&points
        data.update(points=w.points,clock_publishers=sorted(set(w.clock_counts)),independent_receive_age=w.independent_age,semantic_stamps=len(hits),matched_points=len(matched),signal_received=stop)
        ok=stop and len(matched)>=3 and bool(w.clock_counts) and max(w.clock_counts)==1 and w.clock_resets==0 and w.debug_invalid==0 and all(w.metrics.get(k,0)>0 for k in ("diagnostics","inference_latency","result_age","heartbeat_interval"))
        data["status"]="PASS" if ok else "FAIL"
        a.out.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n");w.destroy_node();rclpy.try_shutdown()
    if not ok:raise SystemExit(1)
if __name__=="__main__":main()
