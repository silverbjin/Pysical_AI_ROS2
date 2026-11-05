"""Actual engine rays and asynchronous RGB-D from immutable engine snapshots."""
import math,time,json
from collections import deque
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
from .camera_publisher import FramePublisher
class HeadlessViewer:
 def __init__(self):self.cam=mujoco.MjvCamera();self.closed=False
 def is_running(self):return not self.closed
 def sync(self):pass
 def close(self):self.closed=True
class SensorSuite:
 def __init__(self,model,data,profile,out,latest_camera=False):
  self.latest_camera=latest_camera
  self.capture_stage_timing=deque(maxlen=256);self.capture_stage_total=0
  self.profile=profile;self.out=Path(out);self.next_scan=0.;self.last_scan_ns=None;self.next_rgb=0.;self.scans=0;self.frames=0;self.meta=[];self.first=None;self.last=None;self.node=None;self.camera=None;self.joined=True
  if profile=='vision':
   camera=model.camera('reuse_rgbd').id;self.camera_pos=model.cam_pos[camera].copy()
   optical=Rotation.from_quat(np.roll(model.cam_quat[camera],-1)).as_matrix()@np.diag([1.,-1.,-1.])
   self.camera_quat=Rotation.from_matrix(optical).as_quat()
   self.camera=CameraWorker(model,data.qpos,self.accept_frame,latest=latest_camera,
                            capture_ledger=self.out/'renderer_captures.json' if latest_camera else None)
 def attach(self,node):
  self.node=node;self.scan_pub=node.create_publisher(LaserScan,N+'/scan',1)
  self.publisher=None if self.latest_camera else FramePublisher(node,metadata=self.camera is not None)
 def transforms(self,tf):
  result=[tf('reuse/base','reuse/scan',SCAN_POS,(0.,0.,0.,1.))]
  if self.camera is not None:result.append(tf('reuse/base','reuse/camera_optical',self.camera_pos,self.camera_quat))
  return result
 def request_capture(self,q,stamp,capture_wall):return self.camera.offer(q,stamp,capture_wall)
 def get_capture(self,stamp,timeout):return self.camera.get(stamp,timeout)
 def accept_frame(self,rgb,depth,meta):
  self.frames+=1;self.meta.append(meta);self.last=(rgb,depth,meta)
  if self.first is None:self.first=(rgb.copy(),depth.copy(),dict(meta))
  if self.node is None or self.latest_camera:return
  self.publisher.publish(rgb,depth,meta)
 def step(self,p,state):
  stamp=state['stamp_ns'];sim=stamp/1e9;wall=time.monotonic()
  scan_wall_s=0.
  if wall>=self.next_scan:
   self.next_scan=wall+.1;m=LaserScan();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/scan';m.angle_min=-math.pi;m.angle_max=math.pi;m.angle_increment=2*math.pi/180;m.range_min=.05;m.range_max=4.;m.scan_time=0. if self.last_scan_ns is None else (stamp-self.last_scan_ns)/1e9;self.last_scan_ns=stamp;m.ranges=ray_scan(p.mjModel,p.mjData);self.scan_pub.publish(m);self.scans+=1
   scan_wall_s=time.monotonic()-wall
  if self.camera is not None and wall>=self.next_rgb:
   self.next_rgb=wall+1/15.;q=p.mjData.qpos.copy();state_start=time.monotonic();self.node.publish_state(p,state)
   offer_start=time.monotonic();self.request_capture(q,stamp,wall);finished=time.monotonic()
   if self.latest_camera:
    self.capture_stage_total+=1
    self.capture_stage_timing.append(dict(capture_ns=stamp,capture_wall=wall,scan_wall_s=scan_wall_s,
        state_publish_wall_s=offer_start-state_start,pre_offer_wall_s=offer_start-wall,
        request_offer_wall_s=finished-offer_start,finished_wall=finished))
 def close(self):
  if self.camera is not None:self.joined=self.camera.close()
  if self.latest_camera and self.camera is not None and self.camera.source_captures is not None:self.meta=self.camera.source_captures
  if self.first is not None:write_rgb(self.out/'first_rgb.png',self.first[0]);np.save(self.out/'first_depth.npy',self.first[1])
  if self.latest_camera:
   (self.out/'capture_stage_timing.json').write_text(json.dumps(dict(scope='bounded last256 producer stages; original capture time unchanged',total=self.capture_stage_total,rows=list(self.capture_stage_timing)),indent=2)+'\n')
  summary={'scan_origin':'mj_ray environment group5, body-fixed frame; explicit self/floor filter','camera_origin':'Renderer on immutable actual engine qpos snapshots; single worker/slot, source capture stamp/wall unchanged','scan_count':self.scans,'rgbd_count':self.frames,'camera_worker_joined':self.joined,'camera_worker_pid':None if self.camera is None else self.camera.worker_pid,'camera_tracker_pid':None if self.camera is None else self.camera.tracker_pid,'camera_worker_exit_code':None if self.camera is None else self.camera.process.exitcode,'camera_worker_error':'' if self.camera is None else self.camera.error,'overwritten_waiting_snapshots':0 if self.camera is None else self.camera.overwritten,'camera_pos_base_m':None if self.camera is None else self.camera_pos.tolist(),'camera_optical_quat_base_xyzw':None if self.camera is None else self.camera_quat.tolist(),'latest_camera':self.latest_camera,'overwritten_render_results':0 if self.camera is None else self.camera.output_dropped.value,'captures':self.meta};(self.out/'sensor_summary.json').write_text(json.dumps(summary,indent=2)+'\n');return self.joined
