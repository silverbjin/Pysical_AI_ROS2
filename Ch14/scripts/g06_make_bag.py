"""Actual rosbag2 fixture: pinned real RGB, explicitly synthetic aligned depth and TF."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from sensor_msgs.msg import CameraInfo
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
from builtin_interfaces.msg import Time
from rclpy.serialization import serialize_message
from rosbag2_py import SequentialWriter,StorageOptions,ConverterOptions,TopicMetadata
from cv_bridge import CvBridge
from ch14_ai_common.backends import digest
FIXTURE_SHA="022d2068d525b03a753287c333c09026fe22b9ae6d8071d4e8c757cbed32bdc4"
def main():
    p=argparse.ArgumentParser();p.add_argument("--image",type=Path,required=True);p.add_argument("--bag",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);a=p.parse_args()
    assert digest(a.image)==FIXTURE_SHA and not a.bag.exists()
    rgb=cv2.imread(str(a.image));assert rgb is not None
    h,w=rgb.shape[:2];cv=CvBridge();depth=np.full((h,w),2000,dtype=np.uint16)
    writer=SequentialWriter();writer.open(StorageOptions(uri=str(a.bag),storage_id="sqlite3"),ConverterOptions("cdr","cdr"))
    topics=[("/camera/color/image_raw","sensor_msgs/msg/Image"),("/camera/aligned_depth_to_color/image_raw","sensor_msgs/msg/Image"),("/camera/color/camera_info","sensor_msgs/msg/CameraInfo"),("/tf_static","tf2_msgs/msg/TFMessage")]
    for name,typ in topics:writer.create_topic(TopicMetadata(id=0,name=name,type=typ,serialization_format="cdr",offered_qos_profiles=[]))
    for i in range(40):
        stamp=1_000_000_000+i*200_000_000;t=Time(sec=stamp//10**9,nanosec=stamp%10**9)
        c=CameraInfo(width=w,height=h,k=[500.,0.,w/2,0.,500.,h/2,0.,0.,1.])
        r=cv.cv2_to_imgmsg(rgb,"bgr8");d=cv.cv2_to_imgmsg(depth,"16UC1")
        for m in (r,d,c):m.header.stamp=t;m.header.frame_id="camera_optical"
        tr=TransformStamped();tr.header.stamp=t;tr.header.frame_id="odom";tr.child_frame_id="camera_optical";tr.transform.translation.x=1.;tr.transform.rotation.w=1.
        for (name,_),msg in zip(topics,(r,d,c,TFMessage(transforms=[tr]))):writer.write(name,serialize_message(msg),stamp)
    del writer
    hashes={str(f.relative_to(a.bag)):digest(f) for f in a.bag.rglob("*") if f.is_file()}
    a.receipt.write_text(json.dumps(dict(scope="ACTUAL_ROSBAG2_REPLAY_FIXTURE_SYNTHETIC_DEPTH",image_sha256=FIXTURE_SHA,width=w,height=h,frames=40,topics=dict(topics),records=160,depth_m=2.,tf_x=1.,clock_recorded=False,hashes=hashes),indent=2)+"\n")
if __name__=="__main__":main()
