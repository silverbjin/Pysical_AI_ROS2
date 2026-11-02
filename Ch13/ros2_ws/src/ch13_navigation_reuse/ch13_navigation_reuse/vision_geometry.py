"""Reuse Ch13.4 axial-depth geometry with bounded capture provenance."""
import math
import numpy as np
from integrated_robot_vision.contracts import Box2D,Intrinsics
from integrated_robot_vision.geometry import sample_depth,deproject
class FrameCache:
 def __init__(self):self.frames={};self.owners={};self.last={};self.fault=''
 def insert(self,kind,stamp,wall,gid,payload):
  if self.fault:raise ValueError(self.fault)
  if stamp<=0 or not math.isfinite(wall):self.fault='INVALID_CAPTURE';raise ValueError(self.fault)
  if kind in self.owners and self.owners[kind]!=gid:self.fault='OWNER_REPLACED:'+kind;raise ValueError(self.fault)
  self.owners[kind]=gid
  if stamp<self.last.get(kind,stamp):self.fault='CAPTURE_REORDER:'+kind;raise ValueError(self.fault)
  self.last[kind]=stamp;frame=self.frames.setdefault(stamp,{})
  if kind in frame:return False
  frame[kind]=(payload,wall)
  while len(self.frames)>4:del self.frames[min(self.frames)]
  return True

def admissible(stamp,receipt,clock_ns,wall,tf_stamp):
 return (stamp>0 and all(math.isfinite(x) for x in [receipt,wall]) and 0<=wall-receipt<=.3 and -25_000_000<=clock_ns-stamp<=300_000_000 and 0<=stamp-tf_stamp<=100_000_000)

def red_point(rgb,depth,calibration):
 if rgb.shape!=(240,320,3) or depth.shape!=(240,320):raise ValueError('calibrated320x240 RGB-D required')
 c=rgb.astype(np.float32);mask=(c[:,:,0]>80)&(c[:,:,0]>1.8*c[:,:,1])&(c[:,:,0]>1.8*c[:,:,2]);ys,xs=np.nonzero(mask)
 if len(xs)<20:raise ValueError('red fixture not observed')
 left,right,top,bottom=map(float,[xs.min(),xs.max(),ys.min(),ys.max()]);box=Box2D((left+right)/2,(top+bottom)/2,right-left+1,bottom-top+1,'red_work_object',1.)
 k=Intrinsics(320,240,*map(float,calibration),'reuse_camera_optical','reuse_rgbd_v1');z,_=sample_depth(depth,box);return deproject(box.cx,box.cy,z,k),box

def manipulation_ready(terminal,position_error,yaw_error,settled,observation_ok,fault):
 return terminal==4 and math.isfinite(position_error) and math.isfinite(yaw_error) and position_error<=.1 and yaw_error<=.1 and bool(settled) and bool(observation_ok) and not fault
