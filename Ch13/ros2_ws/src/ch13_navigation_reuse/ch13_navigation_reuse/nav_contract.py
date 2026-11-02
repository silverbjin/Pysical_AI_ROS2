"""Source-preserving lease for controller -> smoother -> safety gateway."""
import math
from .safety import Guard
class NavigationContract:
 def __init__(self):
  self.g=Guard(required=('nav','smooth','scan','tf'),control='nav');self.phase='IDLE';self.edges={};self.smoothed=(0.,0.);self.wait_wall=None
 def trip(self,reason):self.g.trip(reason);self.phase='FAULT'
 def clock(self,stamp,wall,gid):self.g.clock(stamp,wall,gid)
 def graph(self,counts,wall):self.g.graph(counts,wall)
 def tf(self,parent,child,stamp,wall,gid):
  if child in self.edges and self.edges[child]!=(parent,gid):self.trip('TF_EDGE_OWNER:'+child);return
  self.edges[child]=(parent,gid)
  if child=='reuse/base':self.g.observe('tf',stamp,wall,gid)
 def scan(self,stamp,wall,gid,valid=True):self.g.observe('scan',stamp,wall,gid,valid)
 def nav(self,stamp,wall,gid,values,frame=''):
  if frame not in ('','reuse/nav_base'):self.trip('NAV_FRAME');return
  self.g.command(stamp,wall,gid,values,'reuse/nav_base')
 def smooth(self,stamp,wall,gid,values):
  if len(values)!=6 or not all(math.isfinite(x) for x in values) or any(abs(values[i])>1e-10 for i in [1,2,3,4]):self.trip('INVALID_SMOOTHER');return
  if self.g.observe('smooth',stamp,wall,gid):self.smoothed=(max(-.2,min(.2,values[0])),max(-.2,min(.2,values[5])))
 def frames_ready(self):return all(self.edges.get(c,(None,))[0]==p for p,c in [('reuse/map','reuse/odom'),('reuse/odom','reuse/nav_base'),('reuse/nav_base','reuse/base')])
 def enable(self,wall):
  if self.phase!='IDLE' or self.g.mode=='FAULT' or not self.frames_ready():return False
  self.phase='WAITING';self.wait_wall=wall
  for k in ['nav','smooth']:self.g.samples.pop(k,None)
  return True
 def idle(self):
  if self.phase!='FAULT' and self.g.mode!='FAULT':self.phase='IDLE';self.g.mode='DISARMED'
 def output(self,wall):
  if self.g.mode=='FAULT':self.phase='FAULT'
  if self.phase=='WAITING':
   if self.g._fresh(wall):self.phase='ACTIVE';self.g.mode='ARMED'
   elif wall-self.wait_wall>5.:self.trip('NAV_START_TIMEOUT')
  if self.phase=='ACTIVE' and (not self.g._fresh(wall) or not self.frames_ready()):self.trip('NAV_INPUT_TIMEOUT')
  if self.phase=='ACTIVE':return self.g.samples['nav'][0],*self.smoothed,self.phase,self.g.fault
  return self.g.clock_ns,0.,0.,self.phase,self.g.fault
