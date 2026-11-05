"""Actual RGB-D observation with original capture and historical TF provenance."""
import argparse,hashlib,json,math,time,os
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
from sensor_msgs.msg import Image,CameraInfo
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from .camera_native import CameraLink
from geometry_msgs.msg import PointStamped
from .command_gateway import N,ns,set_stamp
from .wire import decode
from .vision_geometry import FrameCache,admissible,red_point
from .image_artifact import write_rgb

def matrix(t):
 q=t.transform.rotation;p=t.transform.translation;a=np.eye(4);a[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();a[:3,3]=[p.x,p.y,p.z];return a
class VisionObserver(Node):
 def __init__(self,inference_hz=10.,target_shape='fixture',latest_camera=False):
  self.target_shape=target_shape;self.last_rejected=None;self.latest_camera=latest_camera
  self.filter_boundary=False
  self.robust_consensus=os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
  self.allow_initial_absence=False
  if self.robust_consensus and target_shape=='cylinder':
   from ch13_system_validation.scenarios import active_scenario
   self.allow_initial_absence=active_scenario().survey_pose is not None
  self.native_counts=Counter();self.packet_counts=Counter()
  super().__init__('ch13_reuse_vision_observer');self.cache=FrameCache();self.camera_link=CameraLink();self.receipt_rows=[];self.clock_ns=0;self.clock_wall=None;self.fault='';self.relay={};self.tf_owners={};self.transforms={};self.map_odom=None;self.last_health=0;self.health_rows=[];self.last_processed=0;self.last_processed_wall=-1e9;self.inference_hz=inference_hz;self.rows=[];self.last_accepted=None;self.rejected=Counter()
  self.observation=self.create_publisher(String,N+'/vision/observation',1);self.point=self.create_publisher(PointStamped,N+'/observed_target',1);self.health=self.create_publisher(String,N+'/vision/health',1);self.status=self.create_publisher(String,N+'/vision/status',1)
  camera_qos=QoSProfile(depth=1 if latest_camera else 2,reliability=ReliabilityPolicy.RELIABLE)
  for kind,typ,topic in [('rgb',Image,'rgb'),('depth',Image,'depth'),('camera_info',CameraInfo,'camera_info'),('camera_meta',String,'camera_capture')]:self.create_subscription(typ,N+'/'+topic,lambda m,k=kind:self.native(k,m),camera_qos)
  self.create_subscription(String,N+'/ingress/vision',lambda m:self.packet(m,'camera'),16)
  if latest_camera:
   for channel in ('vision_clock','vision_tf','vision_tf_static'):
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL) if channel=='vision_tf_static' else 1
    self.create_subscription(String,N+'/ingress/'+channel,lambda m,key=channel:self.packet(m,key),qos)
  else:self.create_subscription(String,N+'/ingress/navigation',lambda m:self.packet(m,'navigation'),16)
  self.create_timer(.02,self.tick,clock=TimerClock(clock_type=ClockType.STEADY_TIME))
 def native(self,kind,message):
  self.native_counts[kind]+=1
  try:
   matched=self.camera_link.native(kind,message)
   if matched:self.camera_frame(*matched)
  except (ValueError,TypeError,KeyError) as exc:self.fault=str(exc)
 def camera_frame(self,key,m,i):
  if key=='camera_meta':payload=json.loads(m.data);stamp=int(payload['capture_ns'])
  else:
   if m.header.frame_id!='reuse/camera_optical' or m.width!=320 or m.height!=240:raise ValueError('camera calibration frame/dimensions')
   stamp=ns(m.header.stamp);payload=m
  if self.cache.insert(key,stamp,i['receipt_wall'],i['publisher_gid'].hex(),payload):self.receipt_rows.append({'kind':key,'capture_ns':stamp,'receipt_wall':i['receipt_wall'],'native_receipt_wall':i['native_receipt_wall'],'canonical_sha256':i['canonical_sha256'],'canonical_bytes':i['canonical_bytes'],'publisher_gid':i['publisher_gid'].hex(),'relay_gid':i['relay_gid'],'source_timestamp':i['source_timestamp']})
  if self.latest_camera and all(k in self.cache.frames.get(stamp,{}) for k in ('rgb','depth','camera_info','camera_meta')):
   # Single-threaded executor: process an eligible complete frame immediately.
   # tick retains the original inference cap, capture/receipt and TF checks.
   self.tick()
 def packet(self,packet,channel):
  self.packet_counts[channel]+=1
  try:
   if channel=='camera':
    matched=self.camera_link.receipt(packet.data)
    if matched:self.camera_frame(*matched)
    return
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
  except (ValueError,TypeError,KeyError) as exc:self.fault=str(exc)
 def tick(self):
  now=time.monotonic()
  if not self.fault and not self.cache.fault:
   # Camera liveness is validated on each complete RGB-D capture, independently
   # of the slower object-inference cap. Goal admission/final READY still need
   # a fresh detected point. Neither channel can renew an old capture's wall time.
   captures=[s for s,f in self.cache.frames.items() if s>self.last_health and all(k in f for k in ['rgb','depth','camera_info','camera_meta'])]
   if captures:
    stamp=max(captures);frame=self.cache.frames[stamp];past=[s for s in self.transforms if s<=stamp and stamp-s<=100_000_000]
    if past and self.clock_wall is not None:
     meta=frame['camera_meta'][0];capture_wall=float(meta['capture_wall']);rgb=frame['rgb'][0];depth=frame['depth'][0];info=frame['camera_info'][0]
     if (capture_wall<=min(v[1] for v in frame.values())+.01 and now-self.clock_wall<=.3 and admissible(stamp,capture_wall,self.clock_ns,now,max(past)) and rgb.encoding=='rgb8' and rgb.step==960 and depth.encoding=='32FC1' and depth.step==1280 and not depth.is_bigendian and hashlib.sha256(bytes(rgb.data)).hexdigest()==meta['rgb_sha256'] and len(rgb.data)==230400 and len(depth.data)==307200 and all(math.isfinite(x) for x in info.k) and info.k[0]>0 and info.k[4]>0):
      self.health.publish(String(data=json.dumps({'capture_ns':stamp,'capture_wall':capture_wall,'scope':'validated_RGBD_capture_and_past_TF'})));self.last_health=stamp;self.health_rows.append({'capture_ns':stamp,'capture_wall':capture_wall,'validation_wall':now,'tf_stamp_ns':max(past),'clock_ns':self.clock_ns})
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
      rgb=np.frombuffer(rgb_bytes,dtype=np.uint8).reshape(240,320,3);depth=np.frombuffer(bytes(depthm.data),dtype='<f4').reshape(240,320);calibration=[info.k[0],info.k[4],info.k[2],info.k[5]];transform=self.transforms[tf_stamp]
      fit=None
      if self.target_shape=='cylinder':
       from ch13_manipulation_reuse.cylinder_vision import fit_cylinder
       from types import SimpleNamespace
       fit=fit_cylinder(rgb,depth,calibration,transform,.02,.08,filter_boundary=self.filter_boundary,robust_consensus=self.robust_consensus)
       optical=np.array(fit['optical_center']);world=np.array(fit['center']);box=SimpleNamespace(**fit['box'])
      else:
       optical,box=red_point(rgb,depth,calibration);world=transform[:3,:3]@optical+transform[:3,3]
      data={'inference_wall':now,'capture_ns':stamp,'capture_wall':capture_wall,'first_receipt_wall':first,'receipt_wall_by_source':{k:v[1] for k,v in frame.items()},'tf_stamp_ns':tf_stamp,'source_frame':'reuse/camera_optical','frame':'reuse/map','optical_point':optical.tolist(),'point':world.tolist(),'T_map_camera':transform.tolist(),'calibration':calibration,'box':{'cx':box.cx,'cy':box.cy,'width':box.width,'height':box.height},'rgb_sha256':digest,'source_gids':dict(self.cache.owners),'source':'actual_Renderer_RGBD_red_fixture'}
      if fit is not None:data.update(source='actual_Renderer_RGBD_known_upright_cylinder_fit',cylinder_fit=fit)
      self.observation.publish(String(data=json.dumps(data)));p=PointStamped();set_stamp(p.header.stamp,stamp);p.header.frame_id='reuse/map';p.point.x,p.point.y,p.point.z=map(float,world);self.point.publish(p);self.rows.append(data);self.last_accepted=(rgb.copy(),depth.copy(),data)
     except (ValueError,IndexError) as exc:
      if str(exc).startswith('cylinder'):
       self.last_rejected=(rgb.copy(),depth.copy(),dict(capture_ns=stamp,capture_wall=capture_wall,
          tf_stamp_ns=tf_stamp,T_map_camera=transform.tolist(),calibration=calibration,reason=str(exc)))
      self.record_rejection(str(exc))
  self.status.publish(String(data=json.dumps({'fault':self.fault or self.cache.fault,'last_capture_ns':self.last_processed,'accepted':len(self.rows),'rejected':dict(self.rejected)})))
 def record_rejection(self,reason):
  self.rejected[reason]+=1
  initial=reason=='cylinder not observed' and self.allow_initial_absence and not self.rows
  if reason in ('red fixture not observed','cylinder not observed') and not initial:self.fault='TARGET_NOT_OBSERVED'
 def diagnostics(self):
  return dict(native_callbacks=dict(self.native_counts),ingress_callbacks=dict(self.packet_counts),
   matched_camera_samples=len(self.receipt_rows),pending_native_by_kind=dict(Counter(k[0] for k in self.camera_link.payloads)),
   pending_receipts_by_kind=dict(Counter(k[0] for k in self.camera_link.receipts)),
   camera_owners=dict(self.camera_link.owners),relay=self.camera_link.relay,
   cached_frames=len(self.cache.frames),tf_samples=len(self.transforms),clock_ns=self.clock_ns,
   last_processed_ns=self.last_processed,last_health_ns=self.last_health)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--report',required=True);ap.add_argument('--inference-hz',type=float,choices=[10.,15.],default=10.);ap.add_argument('--target-shape',choices=['fixture','cylinder'],default='fixture');ap.add_argument('--latest-camera',choices=['true','false'],default='false');args=ap.parse_args();out=Path(args.report).parent;rclpy.init(args=[]);node=VisionObserver(args.inference_hz,args.target_shape,args.latest_camera=='true')
 try:rclpy.spin(node)
 except (KeyboardInterrupt,ExternalShutdownException):pass
 finally:
  if node.last_rejected is not None:
   rgb,depth,meta=node.last_rejected;write_rgb(out/'last_rejected_rgb.png',rgb);np.save(out/'last_rejected_depth.npy',depth);(out/'last_rejected_observation.json').write_text(json.dumps(meta,indent=2)+'\n')
  if node.last_accepted is not None:
   rgb,depth,meta=node.last_accepted;write_rgb(out/'last_accepted_rgb.png',rgb);np.save(out/'last_accepted_depth.npy',depth);(out/'last_accepted_observation.json').write_text(json.dumps(meta,indent=2)+'\n')
  (out/'camera_receipts.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in node.receipt_rows));(out/'camera_health.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in node.health_rows));(out/'vision_observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in node.rows));(out/'vision_summary.json').write_text(json.dumps({'inference_cap_wall_hz':node.inference_hz,'accepted':len(node.rows),'fault':node.fault or node.cache.fault,'rejected':dict(node.rejected),'diagnostics':node.diagnostics()},indent=2)+'\n');node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
