"""Independent DDS witness; no source-counter inference from subscriber counts."""
import argparse,csv,json,time
from pathlib import Path
from collections import Counter,deque
import psutil
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from std_msgs.msg import String,Float32
from rosgraph_msgs.msg import Clock
from diagnostic_msgs.msg import DiagnosticArray
from ch14_ai_common.profiler import real_time_factor

Q=QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
def ns(h):return h.stamp.sec*10**9+h.stamp.nanosec
class Monitor(Node):
    def __init__(self):
        super().__init__("ch14_performance_monitor")
        self.reset()
        self.create_subscription(Image,"/camera/color/image_raw",self.rgb,Q)
        self.create_subscription(Detection2DArray,"/perception/detections",self.det,10)
        self.create_subscription(String,"/perception/heartbeat",self.beat,10)
        self.create_subscription(Clock,"/clock",self.clock,Q)
        self.create_subscription(DiagnosticArray,"/diagnostics",lambda m:self.metrics.update(["diagnostics"]),10)
        for name in ("inference_latency","result_age","heartbeat_interval"):
            self.create_subscription(Float32,"/debug/"+name,lambda m,n=name:self.debug(n,m),10)
    def reset(self):
        self.inputs=[];self.outputs=[];self.heartbeats=[];self.clocks=deque(maxlen=2);self.first_clock=None
        self.clock_resets=0;self.metrics=Counter();self.debug_values={};self.debug_invalid=0
    def rgb(self,m):self.inputs.append(dict(stamp=ns(m.header),wall_ns=time.monotonic_ns(),width=m.width,height=m.height))
    def det(self,m):
        boxes=[]
        for d in m.detections:
            x=d.bbox.center.position.x;y=d.bbox.center.position.y
            for h in d.results:
                boxes.append(dict(label=h.hypothesis.class_id,score=h.hypothesis.score,xyxy=[x-d.bbox.size_x/2,y-d.bbox.size_y/2,x+d.bbox.size_x/2,y+d.bbox.size_y/2]))
        self.outputs.append(dict(stamp=ns(m.header),frame=m.header.frame_id,wall_ns=time.monotonic_ns(),boxes=boxes))
    def beat(self,m):self.heartbeats.append(json.loads(m.data))
    def clock(self,m):
        row=(m.clock.sec*10**9+m.clock.nanosec,time.monotonic_ns())
        if self.clocks and row[0]<self.clocks[-1][0]:self.clock_resets+=1
        if self.first_clock is None:self.first_clock=row
        self.clocks.append(row)
    def debug(self,name,m):
        import math
        if not math.isfinite(m.data) or m.data<0:self.debug_invalid+=1;return
        self.metrics[name]+=1;self.debug_values[name]=float(m.data)
    def spin(self,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:rclpy.spin_once(self,timeout_sec=.005)
    def rtf(self):
        if self.first_clock is None or not self.clocks or self.clock_resets: return None
        return real_time_factor(*[self.first_clock[0],self.clocks[-1][0],self.first_clock[1],self.clocks[-1][1]])
    def snapshot(self):
        return dict(inputs=self.inputs,outputs=self.outputs,heartbeats=self.heartbeats,
                    clock_first=self.first_clock,clock_last=self.clocks[-1] if self.clocks else None,
                    clock_resets=self.clock_resets,rtf=self.rtf(),debug_counts=dict(self.metrics),
                    debug_last=self.debug_values,debug_invalid=self.debug_invalid)
def main():
    p=argparse.ArgumentParser();p.add_argument("--seconds",type=float,default=60.);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if not 0<a.seconds<=600:raise ValueError("seconds")
    rclpy.init();m=Monitor()
    try:m.spin(a.seconds)
    finally:
        a.out.write_text(json.dumps(m.snapshot(),indent=2,allow_nan=False)+"\n");m.destroy_node();rclpy.try_shutdown()
if __name__=="__main__":main()
