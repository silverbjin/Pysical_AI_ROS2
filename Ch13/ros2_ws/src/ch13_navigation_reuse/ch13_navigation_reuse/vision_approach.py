"""Actual RGB-D observation with original capture and historical TF provenance."""
import argparse,hashlib,json,math,time
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.clock import Clock as TimerClock
from rclpy.clock_type import ClockType
from std_msgs.msg import String
from geometry_msgs.msg import PointStamped
from .command_gateway import N,ns,set_stamp
from .wire import decode
from .vision_geometry import FrameCache,admissible,red_point

def matrix(t):
 q=t.transform.rotation;p=t.transform.translation;a=np.eye(4);a[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();a[:3,3]=[p.x,p.y,p.z];return a
class VisionObserver(Node):
 def __init__(self,inference_hz=10.):
  super().__init__('ch13_reuse_vision_observer');self.cache=FrameCache();self.clock_ns=0;self.clock_wall=None;self.fault='';self.relay={};self.tf_owners={};self.transforms={};self.map_odom=None;self.last_processed=0;self.last_processed_wall=-1e9;self.inference_hz=inference_hz;self.rows=[];self.rejected=Counter()
  self.observation=self.create_publisher(String,N+'/vision/observation',1);self.point=self.create_publisher(PointStamped,N+'/observed_target',1);self.health=self.create_publisher(String,N+'/vision/health',1);self.status=self.create_publisher(String,N+'/vision/status',1)
  self.create_subscription(String,N+'/ingress/vision',lambda m:self.packet(m,'camera'),4);self.create_subscription(String,N+'/ingress/navigation',lambda m:self.packet(m,'navigation'),16);self.create_timer(.02,self.tick,clock=TimerClock(clock_type=ClockType.STEADY_TIME))
 def packet(self,packet,channel):
  try:
   key,m,i=decode(packet.data)
   if channel in self.relay and self.relay[channel]!=i['relay_gid']:raise ValueError('relay owner replaced')
   self.relay[channel]=i['relay_gid'];gid=i['publisher_gid'].hex()
   if key=='clock':
    stamp=ns(m.clock)
    if stamp<self.clock_ns:raise ValueError('clock rollback')
    if stamp>self.clock_ns:self.clock_ns=stamp;self.clock_wall=i['receipt_wall']
   elif key in ['tf','tf_static']:
    edges={t.child_frame_id:t for t in m.transforms}
    for child,t in edges.items():
     owner=(t.header.frame_id,gid)
     if child in self.tf_owners and self.tf_owners[child]!=owner:raise ValueError('TF edge owner replaced')
     self.tf_owners[child]=owner
     if child=='reuse/odom' and t.header.frame_id=='reuse/map':self.map_odom=matrix(t)
    needed=['reuse/nav_base','reuse/base','reuse/camera_optical']
    if self.map_odom is not None and all(c in edges for c in needed):
     ts=[ns(edges[c].header.stamp) for c in needed]
     if len(set(ts))!=1:raise ValueError('incoherent capture TF')
     self.transforms[ts[0]]=self.map_odom@matrix(edges[needed[0]])@matrix(edges[needed[1]])@matrix(edges[needed[2]])
     while len(self.transforms)>120:del self.transforms[min(self.transforms)]
   elif key in ['rgb','depth','camera_info','camera_meta']:
    if key=='camera_meta':payload=json.loads(m.data);stamp=int(payload['capture_ns'])
    else:
     if m.header.frame_id!='reuse/camera_optical' or m.width!=320 or m.height!=240:raise ValueError('camera calibration frame/dimensions')
     stamp=ns(m.header.stamp);payload=m
    self.cache.insert(key,stamp,i['receipt_wall'],gid,payload)
  except (ValueError,TypeError,KeyError) as exc:self.fault=str(exc)
 def tick(self):
  now=time.monotonic()
  if not self.fault:
   complete=[s for s,f in self.cache.frames.items() if all(k in f for k in ['rgb','depth','camera_info','camera_meta']) and s>self.last_processed and now-self.last_processed_wall>=1/self.inference_hz]
   if complete:
    stamp=max(complete);frame=self.cache.frames[stamp];past=[s for s in self.transforms if s<=stamp and stamp-s<=100_000_000]
    if past and self.clock_wall is not None:
     tf_stamp=max(past);meta=frame['camera_meta'][0];capture_wall=float(meta['capture_wall']);first=min(f[1] for f in frame.values())
     self.last_processed=stamp;self.last_processed_wall=now
     try:
      if capture_wall>first+.01 or now-self.clock_wall>.3 or not admissible(stamp,capture_wall,self.clock_ns,now,tf_stamp):raise ValueError('capture/clock/TF expired')
      rgbm=frame['rgb'][0];depthm=frame['depth'][0];info=frame['camera_info'][0]
      if rgbm.encoding!='rgb8' or rgbm.step!=960 or depthm.encoding!='32FC1' or depthm.step!=1280 or depthm.is_bigendian:raise ValueError('RGB-D encoding/stride')
      rgb_bytes=bytes(rgbm.data);digest=hashlib.sha256(rgb_bytes).hexdigest()
      if digest!=meta['rgb_sha256']:raise ValueError('capture content mismatch')
      rgb=np.frombuffer(rgb_bytes,dtype=np.uint8).reshape(240,320,3);depth=np.frombuffer(bytes(depthm.data),dtype='<f4').reshape(240,320);calibration=[info.k[0],info.k[4],info.k[2],info.k[5]];optical,box=red_point(rgb,depth,calibration);transform=self.transforms[tf_stamp];world=transform[:3,:3]@optical+transform[:3,3]
      data={'capture_ns':stamp,'capture_wall':capture_wall,'first_receipt_wall':first,'receipt_wall_by_source':{k:v[1] for k,v in frame.items()},'tf_stamp_ns':tf_stamp,'source_frame':'reuse/camera_optical','frame':'reuse/map','optical_point':optical.tolist(),'point':world.tolist(),'T_map_camera':transform.tolist(),'calibration':calibration,'box':{'cx':box.cx,'cy':box.cy,'width':box.width,'height':box.height},'rgb_sha256':digest,'source_gids':dict(self.cache.owners),'source':'actual_Renderer_RGBD_red_fixture'}
      self.observation.publish(String(data=json.dumps(data)));self.health.publish(String(data=json.dumps({'capture_ns':stamp,'capture_wall':capture_wall})));p=PointStamped();set_stamp(p.header.stamp,stamp);p.header.frame_id='reuse/map';p.point.x,p.point.y,p.point.z=map(float,world);self.point.publish(p);self.rows.append(data)
     except (ValueError,IndexError) as exc:self.rejected[str(exc)]+=1
  self.status.publish(String(data=json.dumps({'fault':self.fault or self.cache.fault,'last_capture_ns':self.last_processed,'accepted':len(self.rows),'rejected':dict(self.rejected)})))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--report',required=True);ap.add_argument('--inference-hz',type=float,choices=[10.,15.],default=10.);args=ap.parse_args();out=Path(args.report).parent;rclpy.init(args=[]);node=VisionObserver(args.inference_hz)
 try:rclpy.spin(node)
 except (KeyboardInterrupt,ExternalShutdownException):pass
 finally:
  (out/'vision_observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in node.rows));(out/'vision_summary.json').write_text(json.dumps({'inference_cap_wall_hz':node.inference_hz,'accepted':len(node.rows),'fault':node.fault or node.cache.fault,'rejected':dict(node.rejected)},indent=2)+'\n');node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
