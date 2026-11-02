"""Actual engine rays and asynchronous RGB-D from immutable engine snapshots."""
import math,time,json
from pathlib import Path
import numpy as np,mujoco
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import LaserScan,Image,CameraInfo
from std_msgs.msg import String
from rclpy.qos import QoSProfile,ReliabilityPolicy
from .scene import ray_scan,SCAN_POS,CAM_POS,OPTICAL_R
from .command_gateway import N,set_stamp
from .camera_worker import CameraWorker
from .image_artifact import write_rgb
class HeadlessViewer:
 def __init__(self):self.cam=mujoco.MjvCamera();self.closed=False
 def is_running(self):return not self.closed
 def sync(self):pass
 def close(self):self.closed=True
class SensorSuite:
 def __init__(self,model,data,profile,out):
  self.profile=profile;self.out=Path(out);self.next_scan=0.;self.last_scan_ns=None;self.next_rgb=0.;self.scans=0;self.frames=0;self.meta=[];self.first=None;self.last=None;self.node=None;self.camera=None;self.joined=True
  if profile=='vision':self.camera=CameraWorker(model,data.qpos,self.accept_frame)
 def attach(self,node):
  self.node=node;self.scan_pub=node.create_publisher(LaserScan,N+'/scan',1)
  camera_qos=QoSProfile(depth=2,reliability=ReliabilityPolicy.RELIABLE)
  self.rgb_pub=node.create_publisher(Image,N+'/rgb',camera_qos);self.depth_pub=node.create_publisher(Image,N+'/depth',camera_qos);self.info_pub=node.create_publisher(CameraInfo,N+'/camera_info',camera_qos)
  if self.camera is not None:self.meta_pub=node.create_publisher(String,N+'/camera_capture',camera_qos)
 def transforms(self,tf):
  result=[tf('reuse/base','reuse/scan',SCAN_POS,(0.,0.,0.,1.))]
  if self.camera is not None:result.append(tf('reuse/base','reuse/camera_optical',CAM_POS,Rotation.from_matrix(OPTICAL_R).as_quat()))
  return result
 def request_capture(self,q,stamp,capture_wall):return self.camera.offer(q,stamp,capture_wall)
 def get_capture(self,stamp,timeout):return self.camera.get(stamp,timeout)
 def accept_frame(self,rgb,depth,meta):
  self.frames+=1;self.meta.append(meta);self.last=(rgb,depth,meta)
  if self.first is None:self.first=(rgb.copy(),depth.copy(),dict(meta))
  if self.node is None:return
  stamp=meta['capture_ns']
  for array,encoding,pub in [(rgb,'rgb8',self.rgb_pub),(depth.astype('<f4'),'32FC1',self.depth_pub)]:
   m=Image();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/camera_optical';m.width=320;m.height=240;m.encoding=encoding;m.step=320*(3 if encoding=='rgb8' else 4);m.data=array.tobytes();pub.publish(m)
  self.meta_pub.publish(String(data=json.dumps(meta)));info=CameraInfo();set_stamp(info.header.stamp,stamp);info.header.frame_id='reuse/camera_optical';info.width=320;info.height=240;f=240/(2*math.tan(math.radians(55)/2));info.k=[f,0.,159.5,0.,f,119.5,0.,0.,1.];info.p=[f,0.,159.5,0.,0.,f,119.5,0.,0.,0.,1.,0.];info.distortion_model='plumb_bob';info.d=[0.]*5;self.info_pub.publish(info)
 def step(self,p,state):
  stamp=state['stamp_ns'];sim=stamp/1e9;wall=time.monotonic()
  if wall>=self.next_scan:
   self.next_scan=wall+.1;m=LaserScan();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/scan';m.angle_min=-math.pi;m.angle_max=math.pi;m.angle_increment=2*math.pi/180;m.range_min=.05;m.range_max=4.;m.scan_time=0. if self.last_scan_ns is None else (stamp-self.last_scan_ns)/1e9;self.last_scan_ns=stamp;m.ranges=ray_scan(p.mjModel,p.mjData);self.scan_pub.publish(m);self.scans+=1
  if self.camera is not None and wall>=self.next_rgb:
   self.next_rgb=wall+1/15.;q=p.mjData.qpos.copy();self.node.publish_state(p,state);self.request_capture(q,stamp,wall)
 def close(self):
  if self.camera is not None:self.joined=self.camera.close()
  if self.first is not None:write_rgb(self.out/'first_rgb.png',self.first[0]);np.save(self.out/'first_depth.npy',self.first[1])
  summary={'scan_origin':'mj_ray environment group5, body-fixed frame; explicit self/floor filter','camera_origin':'Renderer on immutable actual engine qpos snapshots; single worker/slot, source capture stamp/wall unchanged','scan_count':self.scans,'rgbd_count':self.frames,'camera_worker_joined':self.joined,'camera_worker_pid':None if self.camera is None else self.camera.worker_pid,'camera_tracker_pid':None if self.camera is None else self.camera.tracker_pid,'camera_worker_exit_code':None if self.camera is None else self.camera.process.exitcode,'camera_worker_error':'' if self.camera is None else self.camera.error,'overwritten_waiting_snapshots':0 if self.camera is None else self.camera.overwritten,'captures':self.meta};(self.out/'sensor_summary.json').write_text(json.dumps(summary,indent=2)+'\n');return self.joined
