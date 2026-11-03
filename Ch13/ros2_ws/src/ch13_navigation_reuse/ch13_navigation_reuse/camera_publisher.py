"""One owner of the original calibrated RGB-D wire representation."""
import json
import math
from sensor_msgs.msg import Image,CameraInfo
from std_msgs.msg import String
from rclpy.qos import QoSProfile,ReliabilityPolicy
from .command_gateway import N,set_stamp


class FramePublisher:
 def __init__(self,node,depth=2,metadata=True):
  qos=QoSProfile(depth=depth,reliability=ReliabilityPolicy.RELIABLE)
  self.rgb=node.create_publisher(Image,N+'/rgb',qos);self.depth=node.create_publisher(Image,N+'/depth',qos)
  self.info=node.create_publisher(CameraInfo,N+'/camera_info',qos)
  self.meta=node.create_publisher(String,N+'/camera_capture',qos) if metadata else None
 def publish(self,rgb,depth,meta):
  stamp=meta['capture_ns']
  for array,encoding,pub in [(rgb,'rgb8',self.rgb),(depth.astype('<f4'),'32FC1',self.depth)]:
   m=Image();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/camera_optical';m.width=320;m.height=240;m.encoding=encoding;m.step=320*(3 if encoding=='rgb8' else 4);m.data=array.tobytes();pub.publish(m)
  if self.meta is not None:self.meta.publish(String(data=json.dumps(meta)))
  info=CameraInfo();set_stamp(info.header.stamp,stamp);info.header.frame_id='reuse/camera_optical';info.width=320;info.height=240;f=240/(2*math.tan(math.radians(55)/2));info.k=[f,0.,159.5,0.,f,119.5,0.,0.,1.];info.p=[f,0.,159.5,0.,0.,f,119.5,0.,0.,0.,1.,0.];info.distortion_model='plumb_bob';info.d=[0.]*5;self.info.publish(info)
