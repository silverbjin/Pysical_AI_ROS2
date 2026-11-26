"""Real DDS installed-node test; real YOLO RGB, synthetic depth only, no Gazebo claim."""
import argparse,json,math,os,signal,subprocess,time
from pathlib import Path
from collections import defaultdict
import cv2,numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from ament_index_python.packages import get_package_prefix
from cv_bridge import CvBridge
from sensor_msgs.msg import Image,CameraInfo
from geometry_msgs.msg import PointStamped,TransformStamped
from vision_msgs.msg import Detection2DArray
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
from tf2_ros import StaticTransformBroadcaster
from ch14_ai_common.yolo_lab import iou
from ch14_ai_perception.rgbd_sync import ns

Q=QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
GT=[2.88,4.67,412.76,552.63]
FRAME="camera_optical"
def stamp(n):
    return Time(sec=n//1_000_000_000,nanosec=n%1_000_000_000)

class Probe(Node):
    def __init__(self,image,out):
        super().__init__("ch14_dds_probe")
        self.bridge=CvBridge();self.image=image;self.out=out;self.h,self.w=image.shape[:2]
        self.rgb=self.create_publisher(Image,"/camera/color/image_raw",Q)
        self.depth=self.create_publisher(Image,"/camera/aligned_depth_to_color/image_raw",Q)
        self.info=self.create_publisher(CameraInfo,"/camera/color/camera_info",Q)
        self.clockpub=self.create_publisher(Clock,"/clock",10)
        self.tf=StaticTransformBroadcaster(self)
        t=TransformStamped();t.header.frame_id="odom";t.child_frame_id=FRAME;t.transform.rotation.w=1.;t.transform.translation.x=1.
        self.tf.sendTransform(t)
        self.ds=[];self.ps=[];self.hs=[];self.anns=[];self.sent={}
        self.create_subscription(Detection2DArray,"/perception/detections",self.on_det,10)
        self.create_subscription(PointStamped,"/perception/target_point",self.on_point,10)
        self.create_subscription(String,"/perception/heartbeat",self.on_heartbeat,10)
        self.create_subscription(Image,"/perception/image_annotated",self.on_ann,Q)
    def on_det(self,m):
        now=self.get_clock().now().nanoseconds
        boxes=[]
        for d in m.detections:
            assert ns(d.header)==ns(m.header) and d.header.frame_id==m.header.frame_id
            x=d.bbox.center.position.x;y=d.bbox.center.position.y
            boxes.append(dict(label=d.results[0].hypothesis.class_id,score=d.results[0].hypothesis.score,
                              xyxy=[x-d.bbox.size_x/2,y-d.bbox.size_y/2,x+d.bbox.size_x/2,y+d.bbox.size_y/2]))
        self.ds.append(dict(stamp=ns(m.header),frame=m.header.frame_id,receive_ns=now,wall=time.monotonic(),boxes=boxes))
    def on_point(self,m):
        self.ps.append(dict(stamp=ns(m.header),frame=m.header.frame_id,xyz=[m.point.x,m.point.y,m.point.z],wall=time.monotonic()))
    def on_heartbeat(self,m):
        self.hs.append(json.loads(m.data))
    def on_ann(self,m):self.anns.append(dict(stamp=ns(m.header),frame=m.header.frame_id,width=m.width,height=m.height))
    def spin(self,seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:rclpy.spin_once(self,timeout_sec=.005)
    def reset(self):
        self.ds.clear();self.ps.clear();self.hs.clear();self.anns.clear();self.sent.clear()
    def send(self,pair=False,n=None,skew=0,kind="good"):
        n=n if n is not None else self.get_clock().now().nanoseconds
        rgb=self.bridge.cv2_to_imgmsg(self.image,encoding="bgr8");rgb.header.stamp=stamp(n);rgb.header.frame_id=FRAME
        if kind=="bad_rgb":rgb.encoding="mono8"
        self.sent[n]=kind
        self.rgb.publish(rgb)
        if pair:
            # Pace distinct DDS writes; retain original source stamps. No retries.
            self.spin(.015)
            z=np.full((self.h,self.w),2.,np.float32)
            if kind=="bad_depth":z[:]=np.nan
            depth=self.bridge.cv2_to_imgmsg(z,encoding="32FC1");depth.header.stamp=stamp(n+skew)
            depth.header.frame_id="wrong_optical" if kind=="bad_frame" else FRAME
            info=CameraInfo();info.header.stamp=stamp(n);info.header.frame_id=FRAME;info.width=self.w;info.height=self.h
            info.k=[400.,0.,self.w/2,0.,400.,self.h/2,0.,0.,1.]
            if kind=="bad_k":info.k=[0.]*9
            self.depth.publish(depth);self.spin(.015);self.info.publish(info)
        return n
    def send_clock(self,n):
        m=Clock();m.clock=stamp(n);self.clockpub.publish(m)
    def wait_ready(self,proc,pair=False):
        until=time.monotonic()+40
        while time.monotonic()<until:
            if proc.poll() is not None:raise RuntimeError("node exited before readiness")
            self.spin(.05)
            if self.hs and self.rgb.get_subscription_count()>0 and (not pair or (self.depth.get_subscription_count()>0 and self.info.get_subscription_count()>0)):
                self.spin(.3);return
        raise TimeoutError("no actual DDS readiness")
    def dump(self,name):
        d=dict(detections=self.ds,points=self.ps,heartbeats=self.hs,annotations=self.anns,sent=self.sent)
        (self.out/(name+".json")).write_text(json.dumps(d,indent=2,allow_nan=False)+"\n")

def start(probe,args,name,mode,delay,pair=False,sim=False,target_frame="odom"):
    probe.spin(.2);probe.reset()
    executable=Path(get_package_prefix("ch14_ai_perception"))/"lib/ch14_ai_perception/detector_node"
    log=(probe.out/(name+".log")).open("w")
    cmd=[str(executable),"--ros-args","-p",f"onnx:={args.onnx}","-p",f"model_sha256:={args.sha256}",
         "-p",f"mode:={mode}","-p",f"delay_ms:={float(delay)}","-p",f"rgbd:={str(pair).lower()}",
         "-p",f"use_sim_time:={str(sim).lower()}","-p",f"target_frame:={target_frame}","-p",f"trace_inputs:={str(pair).lower()}"]
    p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,cwd="/tmp")
    try:probe.wait_ready(p,pair)
    except BaseException:
        stop(probe,p,log,name);raise
    return p,log

def stop(probe,p,log,name):
    if p.poll() is None:p.send_signal(signal.SIGINT)
    try:rc=p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait();rc=-9
    log.close();probe.dump(name)
    lines=(probe.out/(name+".log")).read_text()
    if rc!=0 or "CH14_SHUTDOWN" not in lines:raise AssertionError(f"{name} unclean shutdown {rc}")
    rec=json.loads(lines.split("CH14_SHUTDOWN ")[-1].splitlines()[0])
    assert rec["worker_joined"] and not rec["slot"].get("worker_alive",False)
    return rec

def hit(d):
    return any(b["label"]=="bus" and iou(b["xyxy"],GT)>=.5 for b in d["boxes"])

def burst(probe,args,mode):
    name="burst_"+mode;p,log=start(probe,args,name,mode,150)
    try:
        # fixed frames, source stamps actual ROS time, 30Hz offered load for 8s.
        start_wall=time.monotonic()
        for i in range(240):
            deadline=start_wall+i/30
            while time.monotonic()<deadline:rclpy.spin_once(probe,timeout_sec=min(.002,max(0,deadline-time.monotonic())))
            probe.send()
        probe.spin(.8)
        assert len(probe.ds)>0 and all(hit(d) for d in probe.ds)
        assert all(d["stamp"] in probe.sent and d["frame"]==FRAME for d in probe.ds)
        assert all(a["stamp"] in probe.sent and a["frame"]==FRAME for a in probe.anns)
        assert probe.hs and probe.anns
        ages=[(d["receive_ns"]-d["stamp"])/1e6 for d in probe.ds]
        hb=[h["heartbeat_interval_ms"] for h in probe.hs if h["heartbeat_interval_ms"] is not None]
        assert all(0<=h["last_age_ms"]<=300 for h in probe.hs if h["last_age_ms"] is not None)
        record=dict(sent=240,received_detections=len(probe.ds),subscriber_age_ms=dict(mean=float(np.mean(ages)),p95=float(np.percentile(ages,95)),max=max(ages)),
                    hb_intervals=len(hb),hb_miss_gt_200ms=sum(x>200 for x in hb),hb_max_ms=max(hb),
                    annotation_count=len(probe.anns))
    finally:rec=stop(probe,p,log,name)
    record["shutdown"]=rec
    if mode=="async":
        s=rec["slot"];assert s.get("overwritten",0)>0
        assert s["received"]==s.get("started",0)+s.get("overwritten",0)+s.get("invalidated_pending",0)+s["pending"]
        assert s["started"]==s["completed"]
    return record

def rgbd(probe,args):
    p,log=start(probe,args,"rgbd","async",0,True)
    expected={};bad=[];faults={}
    try:
        for i in range(4):
            n=probe.send(True);expected[n]="good";probe.spin(.25)
        assert probe.ps and all(x["frame"]=="odom" for x in probe.ps)
        for v in probe.ps:
            d=next(d for d in probe.ds if d["stamp"]==v["stamp"])
            box=next(b for b in d["boxes"] if b["label"]=="bus")
            x1,y1,x2,y2=box["xyxy"]
            xyz=[1+((x1+x2)/2-probe.w/2)*2/400,((y1+y2)/2-probe.h/2)*2/400,2.]
            np.testing.assert_allclose(v["xyz"],xyz,atol=1e-6,rtol=0)
            assert hit(d)
        assert all(pnt["stamp"] in expected for pnt in probe.ps)
        for kind in ("bad_depth","bad_frame","bad_k","bad_rgb"):
            n=probe.send(True,kind=kind);bad.append(n);faults[kind]=n;probe.spin(.35)
        # 49ms within tolerance, 51ms outside; depth uses past stamp to avoid future.
        n=probe.send(True,skew=-49_000_000);expected[n]="within";probe.spin(.35)
        assert any(v["stamp"]==n for v in probe.ps)
        n=probe.send(True,skew=-50_000_000);expected[n]="exact_boundary";probe.spin(.35)
        assert any(v["stamp"]==n for v in probe.ps)
        n=probe.send(True,skew=-51_000_000);bad.append(n);faults["skew_51ms"]=n;probe.spin(.4)
        n=probe.send(True,n=probe.get_clock().now().nanoseconds-700_000_000);bad.append(n);faults["stale"]=n;probe.spin(.35)
        n=probe.send(True,n=probe.get_clock().now().nanoseconds+900_000_000);bad.append(n);faults["future"]=n;probe.spin(.35)
        assert not any(v["stamp"] in bad for v in probe.ps)
        assert not any(v["stamp"] in bad[1:] for v in probe.ds)
        assert all(v["stamp"] in expected for v in probe.ps)
        n=probe.send(True);expected[n]="recovery";probe.spin(.35)
        assert any(v["stamp"]==n for v in probe.ps)
        result=dict(valid_points=len(probe.ps),fault_cases=faults,within_49ms=True,exact_50ms=True,outside_51ms=True,
                    zero_fault_points=True,source_header=True,metre_geometry=True,recovered=True,
                    scope="actual ROS DDS RGB image + synthetic aligned depth/static TF")
    finally:rec=stop(probe,p,log,"rgbd")
    result["shutdown"]=rec
    # Every injected fault must reach its intended boundary, not just disappear in DDS.
    lines=(probe.out/"rgbd.log").read_text().splitlines()
    inputs=[json.loads(l.split("CH14_INPUT ",1)[1]) for l in lines if "CH14_INPUT " in l]
    pairs=[json.loads(l.split("CH14_PAIR ",1)[1]) for l in lines if "CH14_PAIR " in l]
    for n in list(faults.values())+list(expected):
        depth_stamp=n-51_000_000 if n==faults["skew_51ms"] else n-49_000_000 if expected.get(n)=="within" else n-50_000_000 if expected.get(n)=="exact_boundary" else n
        for stream,stamp_ in (("rgb",n),("depth",depth_stamp),("info",n)):
            assert any(x["stream"]==stream and x["stamp"]==stamp_ for x in inputs),f"DDS delivery missing {stream} {stamp_}"
        assert any(x["stamps"][0]==n for x in pairs)==(n!=faults["skew_51ms"]),f"ATS boundary {n}"
    for reason in ("INVALID_DEPTH","RGBD_FRAME","CAMERA_K","INVALID_RGB","STALE","FUTURE"):
        assert rec["counters"].get(reason,0)>0,f"missing fault boundary {reason}"
    result["raw_inputs"]=len(inputs);result["matched_pairs"]=len(pairs)
    return result

def missing_tf(probe,args):
    p,log=start(probe,args,"missing_tf","async",0,True,target_frame="missing_frame")
    try:
        n=probe.send(True);probe.spin(.4)
        assert any(d["stamp"]==n and hit(d) for d in probe.ds)
        assert not probe.ps
        assert any(h["status"]=="INVALID_DEPTH_OR_TF" for h in probe.hs)
    finally:rec=stop(probe,p,log,"missing_tf")
    return dict(no_point=True,valid_2d=True,shutdown=rec)

def pause(probe,args):
    p,log=start(probe,args,"clock_pause","async",0,False,True)
    try:
        base=10_000_000_000
        for i in range(10):
            n=base+i*50_000_000;probe.send_clock(n);probe.spin(.02);probe.send(n=n);probe.spin(.03)
        probe.spin(.2)
        assert probe.ds
        probe.spin(.65)
        assert any(h["status"]=="CLOCK_PAUSED" or h["counters"].get("CLOCK_PAUSED",0)>0 for h in probe.hs)
        before=len(probe.ds)
        probe.send(n=n+1);probe.spin(.3)
        assert len(probe.ds)==before
        # rewind epoch, then progress and recover with strictly valid new source timestamps
        for i in range(10):
            n=2_000_000_000+i*50_000_000;probe.send_clock(n);probe.spin(.02);probe.send(n=n);probe.spin(.03)
        probe.spin(.2)
        assert any(d["stamp"]<base for d in probe.ds)
        assert any(h["counters"].get("CLOCK_RESET",0)>0 for h in probe.hs)
    finally:rec=stop(probe,p,log,"clock_pause")
    return dict(pause_blocked=True,rewind_epoch_recovery=True,shutdown=rec)

def main():
    p=argparse.ArgumentParser();p.add_argument("--onnx",type=Path,required=True);p.add_argument("--sha256",required=True);p.add_argument("--image",type=Path,required=True);p.add_argument("--out",type=Path,required=True);p.add_argument("--phase",choices=["all","rgbd"],default="all")
    a=p.parse_args();image=cv2.imread(str(a.image));assert image is not None and image.shape==(640,427,3)
    rclpy.init();probe=Probe(image,a.out);result={}
    try:
        if a.phase=="all":
            for mode in ("sync","async"):
                result[mode]=burst(probe,a,mode)
                (a.out/"dds-summary.json").write_text(json.dumps(result,indent=2)+"\n")
        else:result["reused_t07_run"]=45750110277
        result["rgbd"]=rgbd(probe,a)
        result["missing_tf"]=missing_tf(probe,a)
        result["clock_pause"]=pause(probe,a)
        result["status"]="PASS"
    finally:
        (a.out/"dds-summary.json").write_text(json.dumps(result,indent=2)+"\n")
        probe.destroy_node();rclpy.try_shutdown()
if __name__=="__main__":main()
