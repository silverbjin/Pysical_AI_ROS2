"""Installed replay entrypoints: verified model, readiness, single clock, exec."""
import argparse,json,os,re,time
from pathlib import Path
from ch14_ai_common.backends import digest
def detector():
    p=Path("/models/yolov8n.onnx");h=os.environ["MODEL_SHA256"]
    if not re.fullmatch("[0-9a-f]{64}",h) or digest(p)!=h:raise ValueError("model hash mismatch")
    from ament_index_python.packages import get_package_prefix
    exe=str(Path(get_package_prefix("ch14_ai_perception"))/"lib/ch14_ai_perception/detector_node")
    os.execv(exe,[exe,"--ros-args","-r","__node:=yolo_detector_node","-p","model_path:="+str(p),"-p","model_sha256:="+h,"-p","backend:=ort","-p","mode:=async","-p","rgbd:=true","-p","use_sim_time:=true","-p","target_class:=bus","-p","target_frame:=odom","-p","profile_timing:=true"])
def ready(timeout):
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    rclpy.init();n=Node("ch14_replay_gate");heart=[]
    sub=n.create_subscription(String,"/perception/heartbeat",lambda m:heart.append(json.loads(m.data)),10)
    try:
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            rclpy.spin_once(n,timeout_sec=.1)
            if n.count_publishers("/clock")>0:raise RuntimeError("existing clock publisher; replay forbidden")
            names=n.get_node_names()
            if heart and heart[-1].get("model_sha256")==os.environ["MODEL_SHA256"] and "ch14_performance_monitor" in names and heart[-1].get("det_subscribers",0)>0 and n.count_subscribers("/camera/color/image_raw")>=2 and n.count_subscribers("/camera/aligned_depth_to_color/image_raw")>0:
                print(json.dumps(dict(status="READY",nodes=names,clock_publishers=0,det_subscribers=heart[-1]["det_subscribers"])),flush=True);return
        raise RuntimeError("DDS readiness timeout; bag NOT_STARTED")
    finally:n.destroy_node();rclpy.try_shutdown()
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=["detector","ready","sensor"]);p.add_argument("--timeout",type=float,default=25.);a=p.parse_args()
    if a.action=="detector":detector()
    else:
        ready(a.timeout)
        if a.action=="sensor":
            cmd=["ros2","bag","play","/bags/ch14_rgbd","--clock","100","--delay","1","--disable-keyboard-controls","--qos-profile-overrides-path","/opt/ch14/playback_qos.yaml"]
            os.execvp(cmd[0],cmd)
if __name__=="__main__":main()
