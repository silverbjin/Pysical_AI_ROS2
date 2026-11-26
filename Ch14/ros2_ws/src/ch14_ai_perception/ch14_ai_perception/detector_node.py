"""T07/T08: ROS callbacks never block on inference in async mode."""
import json,time,sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.time import Time
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from rclpy.executors import SingleThreadedExecutor
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Image,CameraInfo
from vision_msgs.msg import Detection2DArray,Detection2D,ObjectHypothesisWithPose
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
from diagnostic_msgs.msg import DiagnosticArray,DiagnosticStatus,KeyValue
from cv_bridge import CvBridge
from message_filters import Subscriber,ApproximateTimeSynchronizer
from tf2_ros import Buffer,TransformListener,TransformException
from ch14_ai_common.backends import OrtBackend,NAMES
from ch14_ai_common.yolo import preprocess,postprocess
from .latest_slot import LatestSlot
from .freshness import Freshness
from .rgbd_sync import ns,validate_pair,point_from_detection,transform_matrix,transform_point

SENSOR=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
SYNC_QOS=QoSProfile(depth=10,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)

@dataclass(frozen=True)
class Frame:
    header:object
    stamp:int
    epoch:int
    image:np.ndarray
    intr:object=None
    depth:object=None
    oldest_stamp:int=0

class Detector(Node):
    def __init__(self):
        super().__init__("ch14_detector")
        defaults=dict(onnx="",model_sha256="",backend="ort",mode="async",rgbd=False,
                      target_frame="odom",target_class="bus",threads=2,delay_ms=0.,
                      annotation=True,trace_inputs=False,sensor_reliability="best_effort")
        for k,v in defaults.items():self.declare_parameter(k,v)
        p={k:self.get_parameter(k).value for k in defaults}
        if p["mode"] not in ("sync","async") or p["backend"] not in ("ort","openvino"):raise ValueError("mode/backend")
        if p["target_class"] not in NAMES or not p["target_frame"] or not 0<=p["delay_ms"]<=1000:raise ValueError("target or delay")
        if p["sensor_reliability"] not in ("best_effort","reliable"):raise ValueError("sensor_reliability")
        # Production default remains sensor BEST_EFFORT; reliable only for explicit deterministic replay.
        reliability=ReliabilityPolicy.RELIABLE if p["sensor_reliability"]=="reliable" else ReliabilityPolicy.BEST_EFFORT
        sensor_q=QoSProfile(depth=1,reliability=reliability,durability=DurabilityPolicy.VOLATILE)
        sync_q=QoSProfile(depth=10,reliability=reliability,durability=DurabilityPolicy.VOLATILE)
        self.p=p;self.bridge=CvBridge();self.count=Counter();self.last_status="STARTING";self.last_age=None
        self.guard=Freshness(self.get_parameter("use_sim_time").value)
        self.last_published=0;self.pause_latched=False;self.heartbeat_ns=None
        self.tf=Buffer(node=self);self.listener=TransformListener(self.tf,self)
        if p["backend"]=="ort":self.backend=OrtBackend(Path(p["onnx"]),p["model_sha256"],p["threads"])
        else:
            from ch14_ai_common.ov_backend import OpenVinoBackend
            self.backend=OpenVinoBackend(Path(p["onnx"]),p["model_sha256"],p["threads"])
        self.backend.forward(np.zeros((1,3,640,640),np.float32))
        self.dets=self.create_publisher(Detection2DArray,"/perception/detections",10)
        self.annot=self.create_publisher(Image,"/perception/image_annotated",SENSOR)
        self.target=self.create_publisher(PointStamped,"/perception/target_point",10)
        self.diag=self.create_publisher(DiagnosticArray,"/perception/diagnostics",10)
        self.heartbeat=self.create_publisher(String,"/perception/heartbeat",10)
        self.slot=LatestSlot(self.infer) if p["mode"]=="async" else None
        if p["rgbd"]:
            self.subs=[Subscriber(self,Image,"/camera/color/image_raw",qos_profile=sync_q),
                       Subscriber(self,Image,"/camera/aligned_depth_to_color/image_raw",qos_profile=sync_q),
                       Subscriber(self,CameraInfo,"/camera/color/camera_info",qos_profile=sync_q)]
            if p["trace_inputs"]:
                for label,sub in zip(("rgb","depth","info"),self.subs):
                    sub.registerCallback(lambda msg,label=label:self.trace_input(label,msg))
            # ATS uses strict < slop; one nanosecond includes exactly 50ms.
            self.sync=ApproximateTimeSynchronizer(self.subs,10,.050000001)
            self.sync.registerCallback(self.receive_pair)
        else:self.sub=self.create_subscription(Image,"/camera/color/image_raw",self.receive,sensor_q)
        self.steady=Clock(clock_type=ClockType.STEADY_TIME)
        self.poll=self.create_timer(.01,self.tick,clock=self.steady)
        self.hb=self.create_timer(.1,self.beat,clock=self.steady)
        self.last_status="READY"
        self.get_logger().info("CH14_READY")

    def now(self):return self.get_clock().now().nanoseconds
    def invalidate(self,reason):
        self.count[reason]+=1;self.last_status=reason
        self.guard.invalidate()
        if self.slot:self.slot.invalidate()

    def clock(self):
        now=self.now();wall=time.monotonic_ns()
        if self.guard.observe(now,wall):
            self.last_published=0
            self.count["CLOCK_RESET"]+=1;self.last_status="CLOCK_RESET"
            if self.slot:self.slot.invalidate()
        paused=self.guard.sim_time and wall-self.guard.last_progress>=self.guard.pause_ns
        if paused and not self.pause_latched:self.invalidate("CLOCK_PAUSED")
        self.pause_latched=paused
        return now,wall

    def trace_input(self,label,msg):
        print("CH14_INPUT",json.dumps(dict(stream=label,stamp=ns(msg.header),frame=msg.header.frame_id,wall_ns=time.monotonic_ns())),flush=True)

    def receive_pair(self,rgb,depth,info):
        self.count["matched_pairs"]+=1
        if self.p["trace_inputs"]:
            print("CH14_PAIR",json.dumps(dict(stamps=[ns(x.header) for x in (rgb,depth,info)],wall_ns=time.monotonic_ns())),flush=True)
        try:intr,z=validate_pair(rgb,depth,info)
        except ValueError as e:
            self.count["invalid_pair"]+=1;self.invalidate(str(e));return
        # Reject a fresh RGB matched to a future/stale depth or calibration.
        now,wall=self.clock()
        for msg in (depth,info):
            reason=self.guard.check(ns(msg.header),now,wall,self.guard.epoch)
            if reason:self.invalidate(reason);return
        self.receive(rgb,intr,z,min(ns(m.header) for m in (rgb,depth,info)))

    def receive(self,msg,intr=None,depth=None,oldest_stamp=None):
        self.count["callbacks"]+=1
        if self.p["trace_inputs"] and not self.p["rgbd"]:self.trace_input("rgb",msg)
        now,wall=self.clock();stamp=ns(msg.header)
        reason=self.guard.accept(stamp,now,wall)
        if reason:self.invalidate(reason);return
        try:
            if not msg.header.frame_id or msg.encoding not in ("bgr8","rgb8") or msg.width<=0 or msg.height<=0 or msg.step<3*msg.width or len(msg.data)!=msg.step*msg.height:raise ValueError("RGB_ENCODING_OR_LAYOUT")
            image=np.array(self.bridge.imgmsg_to_cv2(msg,desired_encoding="bgr8"),copy=True)
            if image.shape!=(msg.height,msg.width,3):raise ValueError("RGB_SHAPE")
        except Exception:
            self.invalidate("INVALID_RGB");return
        frame=Frame(msg.header,stamp,self.guard.epoch,image,intr,depth,oldest_stamp or stamp)
        self.count["accepted"]+=1
        if self.slot:self.slot.put(frame)
        else:
            self.count["sync_started"]+=1
            try:result=(frame,self.infer(frame),None)
            except Exception as e:result=(frame,None,str(e))
            self.emit(result)

    def infer(self,frame):
        start=time.monotonic_ns()
        if self.p["delay_ms"]:time.sleep(self.p["delay_ms"]/1000)
        x,meta=preprocess(frame.image)
        detections=postprocess(self.backend.forward(x),meta,.5,.45)
        return detections,(time.monotonic_ns()-start)/1e6

    def tick(self):
        self.clock()
        if self.slot:
            result=self.slot.pop()
            if result:self.emit(result)

    def emit(self,result):
        frame,payload,error=result;now,wall=self.clock()
        reason=self.guard.check(frame.oldest_stamp,now,wall,frame.epoch)
        if reason or frame.stamp<=self.last_published:
            self.count[reason or "RESULT_OUT_OF_ORDER"]+=1;return
        if error:self.count["INFERENCE_ERROR"]+=1;self.last_status="INFERENCE_ERROR";return
        ds,ms=payload
        point=None;target_status="NO_TARGET"
        if self.p["rgbd"]:
            for d in ds:
                if NAMES[d.class_id]!=self.p["target_class"]:continue
                try:
                    xyz,mad=point_from_detection(d,frame.intr,frame.depth)
                    target_frame=self.p["target_frame"]
                    if target_frame!=frame.header.frame_id:
                        tr=self.tf.lookup_transform(target_frame,frame.header.frame_id,Time.from_msg(frame.header.stamp))
                        xyz=transform_point(xyz,transform_matrix(tr.transform))
                    point=PointStamped();point.header.stamp=frame.header.stamp;point.header.frame_id=target_frame
                    point.point.x,point.point.y,point.point.z=map(float,xyz)
                    target_status="TRACKED";break
                except ValueError:
                    self.count["INVALID_DEPTH"]+=1;target_status="INVALID_DEPTH_OR_TF"
                except TransformException:
                    self.count["TF_UNAVAILABLE"]+=1;target_status="INVALID_DEPTH_OR_TF"
        msg=Detection2DArray();msg.header=frame.header
        annotated=frame.image.copy() if self.p["annotation"] else None
        for d in ds:
            x1,y1,x2,y2=d.xyxy
            det=Detection2D();det.header=frame.header;det.bbox.center.position.x=(x1+x2)/2;det.bbox.center.position.y=(y1+y2)/2
            det.bbox.size_x=x2-x1;det.bbox.size_y=y2-y1
            hyp=ObjectHypothesisWithPose();hyp.hypothesis.class_id=NAMES[d.class_id];hyp.hypothesis.score=d.confidence
            det.results.append(hyp);msg.detections.append(det)
            if annotated is not None:
                cv2.rectangle(annotated,(round(x1),round(y1)),(round(x2),round(y2)),(0,255,0),2)
                cv2.putText(annotated,NAMES[d.class_id],(round(x1),max(12,round(y1))),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,0),1)
        ann=self.bridge.cv2_to_imgmsg(annotated,encoding="bgr8") if annotated is not None else None
        if ann is not None:ann.header=frame.header
        # Final freshness check after geometry/annotation work, not only inference.
        now,wall=self.clock();reason=self.guard.check(frame.oldest_stamp,now,wall,frame.epoch)
        if reason:self.count[reason]+=1;return
        if self.p["trace_inputs"]:
            print("CH14_EMIT",json.dumps(dict(stamp=frame.stamp,oldest_stamp=frame.oldest_stamp,ros_ns=now,age_ms=(now-frame.stamp)/1e6,oldest_age_ms=(now-frame.oldest_stamp)/1e6,epoch=frame.epoch,target=point is not None,labels=[NAMES[d.class_id] for d in ds],detection_count=len(ds))),flush=True)
        self.dets.publish(msg)
        if ann is not None:self.annot.publish(ann)
        if point is not None:self.target.publish(point);self.count["targets"]+=1
        self.last_published=frame.stamp;self.last_age=(now-frame.stamp)/1e6
        self.count["published"]+=1;self.last_status=target_status if self.p["rgbd"] else "DETECTION"
        self.last_infer_ms=ms

    def beat(self):
        now,wall=self.clock()
        interval=(wall-self.heartbeat_ns)/1e6 if self.heartbeat_ns else None
        self.heartbeat_ns=wall
        if interval is not None and interval>200:self.count["heartbeat_deadline_miss"]+=1
        if self.last_published and now-self.last_published>300_000_000:self.last_status="STALE_NO_OUTPUT"
        record=dict(status=self.last_status,epoch=self.guard.epoch,ros_ns=now,wall_ns=wall,
                    heartbeat_interval_ms=interval,last_age_ms=self.last_age,last_infer_ms=getattr(self,"last_infer_ms",None),
                    counters=dict(self.count),slot=self.slot.snapshot() if self.slot else {},mode=self.p["mode"],backend=self.p["backend"],det_subscribers=self.dets.get_subscription_count(),point_subscribers=self.target.get_subscription_count())
        s=String();s.data=json.dumps(record);self.heartbeat.publish(s)
        a=DiagnosticArray();a.header.stamp=self.get_clock().now().to_msg()
        st=DiagnosticStatus();st.name="ch14/perception";st.hardware_id="simulation_or_replay"
        st.level=DiagnosticStatus.OK if self.last_status in ("READY","DETECTION","TRACKED","NO_TARGET") else DiagnosticStatus.WARN
        st.message=self.last_status;st.values=[KeyValue(key="evidence",value=s.data)];a.status=[st];self.diag.publish(a)

    def close(self):
        return self.slot.close(10) if self.slot else True

def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    import signal
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    node=None;ex=SingleThreadedExecutor()
    try:
        node=Detector();ex.add_node(node)
        while rclpy.ok() and not stopping:ex.spin_once(timeout_sec=.05)
    finally:
        if node is not None:
            ok=node.close()
            print("CH14_SHUTDOWN",json.dumps({"worker_joined":ok,"counters":dict(node.count),"slot":node.slot.snapshot() if node.slot else {}}),flush=True)
            ex.remove_node(node);node.destroy_node()
        else:ok=False
        ex.shutdown();rclpy.try_shutdown()
        if not ok:raise SystemExit(1)
