"""Observe real Gazebo RGB-D through DDS. Independent isolated depth silhouette GT."""
import argparse,json,time,subprocess
from pathlib import Path
from collections import OrderedDict
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from sensor_msgs.msg import Image,CameraInfo
from vision_msgs.msg import Detection2DArray
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from cv_bridge import CvBridge
from ch14_ai_perception.rgbd_sync import ns,validate_pair
from ch14_ai_common.yolo_lab import iou

Q=QoSProfile(depth=20,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
def control(paused):
    r=subprocess.run(["gz","service","-s","/world/ch14_semantic/control","--reqtype","gz.msgs.WorldControl","--reptype","gz.msgs.Boolean","--timeout","2000","--req",f"pause: {str(paused).lower()}"],capture_output=True,text=True,timeout=5)
    if r.returncode!=0 or "true" not in r.stdout:raise RuntimeError("Gazebo world control failed: "+r.stdout+r.stderr)
    return r.stdout
class Witness(Node):
    def __init__(self,out):
        super().__init__("ch14_gazebo_witness")
        self.out=out;self.cv=CvBridge();self.maps={k:OrderedDict() for k in ("rgb","depth","info","det","point","ann")}
        self.hb=[];self.clocks=[];self.det_order=[];self.count={k:0 for k in self.maps}
        for key,typ,topic in [("rgb",Image,"/camera/color/image_raw"),("depth",Image,"/camera/aligned_depth_to_color/image_raw"),("info",CameraInfo,"/camera/color/camera_info"),("det",Detection2DArray,"/perception/detections"),("point",PointStamped,"/perception/target_point"),("ann",Image,"/perception/image_annotated")]:
            self.create_subscription(typ,topic,lambda m,k=key:self.record(k,m),Q)
        self.create_subscription(String,"/perception/heartbeat",lambda m:self.hb.append(json.loads(m.data)),10)
        self.create_subscription(Clock,"/clock",lambda m:self.clocks.append((time.monotonic(),int(m.clock.sec)*10**9+m.clock.nanosec)),Q)
    def record(self,k,m):
        n=ns(m.header);self.count[k]+=1;self.maps[k][n]=m
        if k=="det":self.det_order.append(n)
        while len(self.maps[k])>48:self.maps[k].popitem(last=False)
    def spin(self,seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:rclpy.spin_once(self,timeout_sec=.01)
    def evaluate(self,n):
        maps=self.maps
        rgb,depth,info=(maps[k].get(n) for k in ("rgb","depth","info"))
        if rgb is None or depth is None or info is None:return None
        intr,z=validate_pair(rgb,depth,info)
        if intr.frame_id!="camera_optical":raise AssertionError("wrong optical frame")
        img=self.cv.imgmsg_to_cv2(rgb,desired_encoding="bgr8")
        mask=np.isfinite(z)&(z>=.1)&(z<4.9)
        vs,us=np.nonzero(mask)
        if len(us)<100:raise AssertionError("no actual isolated mesh depth silhouette")
        gt=[int(us.min()),int(vs.min()),int(us.max()+1),int(vs.max()+1)]
        # Independent RGB foreground sanity check: same camera, uniform backdrop, no other geometry.
        border=np.concatenate([img[0],img[-1],img[:,0],img[:,-1]],axis=0).astype(float)
        bg=np.median(border,axis=0);rgbmask=np.max(np.abs(img.astype(float)-bg),axis=2)>15
        union=np.count_nonzero(mask|rgbmask)
        alignment=np.count_nonzero(mask&rgbmask)/union if union else 0.
        det=maps["det"][n];hits=[]
        if det.header.frame_id!=intr.frame_id:raise AssertionError("det header mismatch")
        for d in det.detections:
            if ns(d.header)!=n or d.header.frame_id!=intr.frame_id:raise AssertionError("nested header mismatch")
            x=d.bbox.center.position.x;y=d.bbox.center.position.y
            box=[x-d.bbox.size_x/2,y-d.bbox.size_y/2,x+d.bbox.size_x/2,y+d.bbox.size_y/2]
            label=d.results[0].hypothesis.class_id;score=d.results[0].hypothesis.score
            hits.append(dict(label=label,score=score,bbox=box,gt_iou=iou(box,gt)))
        person=next((d for d in hits if d["label"]=="person" and d["gt_iou"]>=.5),None)
        point=maps["point"].get(n)
        xyz=None;point_ok=False
        if person and point is not None:
            xyz=[point.point.x,point.point.y,point.point.z]
            # TF is independent analytic optical->world convention; X_world=Z_optical.
            box=person["bbox"];u=(box[0]+box[2])/2;v=(box[1]+box[3])/2
            col=int(np.floor(u+.5));row=int(np.floor(v+.5))
            patch=z[max(0,row-2):row+3,max(0,col-2):col+3];p=patch[np.isfinite(patch)&(patch>=.1)&(patch<=5)]
            if p.size>=5:
                zz=float(np.median(p));expected=[zz,-(u-intr.cx)*zz/intr.fx,1-(v-intr.cy)*zz/intr.fy]
                point_ok=point.header.frame_id=="odom" and np.allclose(xyz,expected,atol=1e-5,rtol=0) and 1.5<xyz[0]<3.5
        return dict(stamp=n,gt_bbox=gt,depth_pixels=int(mask.sum()),alignment_iou=float(alignment),detections=hits,
                    semantic_hit=person is not None,point_xyz=xyz,point_ok=bool(point_ok),
                    status="PASS" if person and point_ok and alignment>=.7 else "FAIL")
    def collect(self,num,after=0,timeout=40):
        until=time.monotonic()+timeout;rows=[];seen=set()
        while time.monotonic()<until and len(rows)<num:
            self.spin(.05)
            for n in self.det_order:
                if n<=after or n in seen:continue
                if n not in self.maps["det"]:raise RuntimeError("witness buffer overflow")
                row=self.evaluate(n)
                if row is None:continue
                if row["semantic_hit"] and n not in self.maps["point"] and time.monotonic()<until-.5:continue
                rows.append(row);seen.add(n)
                if len(rows)==num:break
        return rows
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    rclpy.init();w=Witness(a.out);result={}
    try:
        normal=w.collect(10)
        result["normal"]=normal
        result["counts_before_pause"]=dict(w.count)
        if len(normal)!=10 or not all(x["status"]=="PASS" for x in normal):raise RuntimeError("actual semantic/geometry/alignment not accepted")
        # Preserve only derived rendered sample, not source texture/mesh bytes. Attribution in scene receipt.
        n=normal[0]["stamp"]
        if n in w.maps["ann"]:
            cv2.imwrite(str(a.out/"rendered-annotated.png"),w.cv.imgmsg_to_cv2(w.maps["ann"][n],desired_encoding="bgr8"))
        result["pause_response"]=control(True);w.spin(.75)
        before=w.count["det"];clk=w.clocks[-1][1];w.spin(.6)
        result["pause"]=dict(clock_constant=w.clocks[-1][1]==clk,no_new_valid_output=w.count["det"]==before,
            pause_guard=any(h["counters"].get("CLOCK_PAUSED",0)>0 for h in w.hb))
        if not all(result["pause"].values()):raise RuntimeError("pause guard failed")
        result["resume_response"]=control(False)
        resumed=w.collect(3,after=clk)
        result["resumed"]=resumed
        if len(resumed)!=3 or not all(x["status"]=="PASS" for x in resumed):raise RuntimeError("resume semantic or geometry failed")
        result["status"]="PASS"
    finally:
        result["counts"]=w.count;result["heartbeats"]=w.hb;result["clock_samples"]=len(w.clocks)
        (a.out/"gazebo-witness.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        w.destroy_node();rclpy.try_shutdown()
if __name__=="__main__":main()
