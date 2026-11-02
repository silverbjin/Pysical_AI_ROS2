"""Actual engine ray and RGB-D sensors. No scene labels enter detections."""
import math,time,hashlib,json,struct,zlib
from pathlib import Path
import numpy as np,mujoco
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import LaserScan,Image,CameraInfo
from std_msgs.msg import String
from rclpy.qos import qos_profile_sensor_data
from .scene import ray_scan,SCAN_POS,CAM_POS,OPTICAL_R
from .command_gateway import N,set_stamp
class HeadlessViewer:
 def __init__(self):self.cam=mujoco.MjvCamera();self.closed=False
 def is_running(self):return not self.closed
 def sync(self):pass
 def close(self):self.closed=True
class SensorSuite:
 def __init__(self,model,data,profile,out):
  self.profile=profile;self.out=Path(out);self.next_scan=0.;self.next_rgb=0.;self.scans=0;self.frames=0;self.renderer=None;self.meta=[]
  if profile=='vision':
   self.option=mujoco.MjvOption();self.option.geomgroup[5]=1;self.renderer=mujoco.Renderer(model,height=240,width=320);self.renderer.update_scene(data,camera='reuse_rgbd',scene_option=self.option);self.renderer.render();self.renderer.enable_depth_rendering();self.renderer.render();self.renderer.disable_depth_rendering()
 def attach(self,node):
  self.node=node;self.scan_pub=node.create_publisher(LaserScan,N+'/scan',1)
  self.rgb_pub=node.create_publisher(Image,N+'/rgb',qos_profile_sensor_data);self.depth_pub=node.create_publisher(Image,N+'/depth',qos_profile_sensor_data);self.info_pub=node.create_publisher(CameraInfo,N+'/camera_info',qos_profile_sensor_data)
  if self.renderer is not None:self.meta_pub=node.create_publisher(String,N+'/camera_capture',1)
 def transforms(self,tf):
  result=[tf('reuse/base','reuse/scan',SCAN_POS,(0.,0.,0.,1.))]
  if self.renderer is not None:result.append(tf('reuse/base','reuse/camera_optical',CAM_POS,Rotation.from_matrix(OPTICAL_R).as_quat()))
  return result
 def step(self,p,state):
  stamp=state['stamp_ns'];sim=stamp/1e9
  if sim>=self.next_scan:
   self.next_scan=sim+.1;m=LaserScan();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/scan';m.angle_min=-math.pi;m.angle_max=math.pi;m.angle_increment=2*math.pi/180;m.range_min=.05;m.range_max=4.;m.scan_time=.1;m.ranges=ray_scan(p.mjModel,p.mjData);self.scan_pub.publish(m);self.scans+=1
  if self.renderer is not None and sim>=self.next_rgb:
   self.next_rgb=sim+1/15.;self.node.publish_state(p,state)
   capture_wall=time.monotonic();self.renderer.update_scene(p.mjData,camera='reuse_rgbd',scene_option=self.option);rgb=self.renderer.render().copy();self.renderer.enable_depth_rendering();depth=self.renderer.render().copy();self.renderer.disable_depth_rendering()
   for array,encoding,pub in [(rgb,'rgb8',self.rgb_pub),(depth.astype('<f4'),'32FC1',self.depth_pub)]:
    m=Image();set_stamp(m.header.stamp,stamp);m.header.frame_id='reuse/camera_optical';m.width=320;m.height=240;m.encoding=encoding;m.step=320*(3 if encoding=='rgb8' else 4);m.data=array.tobytes();pub.publish(m)
   self.meta_pub.publish(String(data=json.dumps({'capture_ns':stamp,'capture_wall':capture_wall,'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest()})))
   info=CameraInfo();set_stamp(info.header.stamp,stamp);info.header.frame_id='reuse/camera_optical';info.width=320;info.height=240;f=240/(2*math.tan(math.radians(55)/2));info.k=[f,0.,159.5,0.,f,119.5,0.,0.,1.];info.p=[f,0.,159.5,0.,0.,f,119.5,0.,0.,0.,1.,0.];info.distortion_model='plumb_bob';info.d=[0.]*5;self.info_pub.publish(info)
   self.frames+=1;self.meta.append({'capture_ns':stamp,'capture_wall':capture_wall,'render_finished_wall':time.monotonic(),'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest()})
   if self.frames==1:
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    image=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',320,240,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in rgb)))+chunk(b'IEND',b'')
    (self.out/'first_rgb.png').write_bytes(image);np.save(self.out/'first_depth.npy',depth)
 def close(self):
  if self.renderer is not None:self.renderer.close()
  (self.out/'sensor_summary.json').write_text(json.dumps({'scan_origin':'mj_ray environment group5, body-fixed frame; explicit self/floor filter','camera_origin':'MuJoCo Renderer RGB and axial depth','scan_count':self.scans,'rgbd_count':self.frames,'captures':self.meta},indent=2)+'\n')
