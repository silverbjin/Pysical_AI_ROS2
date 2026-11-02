"""Source-preserving lease for controller -> smoother -> safety gateway."""
import math
from .safety import Guard
class NavigationContract:
 def __init__(self):
  self.g=Guard(required=('nav','smooth','scan','tf'),control='nav');self.phase='IDLE';self.edges={};self.smoothed=(0.,0.);self.wait_wall=None;self.last_output_ns=0;self.last_output=(0.,0.)
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
  nav=self.g.samples.get('nav');smooth=self.g.samples.get('smooth')
  candidate=min(nav[0],smooth[0]) if nav and smooth else None
  if self.phase=='WAITING':
   if self.g._fresh(wall) and candidate>=self.last_output_ns:self.phase='ACTIVE';self.g.mode='ARMED'
   elif wall-self.wait_wall>5.:self.trip('NAV_START_TIMEOUT')
  if self.phase=='ACTIVE' and (not self.g._fresh(wall) or not self.frames_ready()):self.trip('NAV_INPUT_TIMEOUT')
  if self.phase=='ACTIVE':
   if candidate>=self.last_output_ns:self.last_output_ns=candidate;self.last_output=self.smoothed
   return self.last_output_ns,*self.last_output,self.phase,self.g.fault
  # IDLE is explicitly synthetic. During handoff, freeze its high-water mark
  # once a controller sample arrives; never re-stamp that older command.
  if not (self.phase=='WAITING' and nav):self.last_output_ns=max(self.last_output_ns,self.g.clock_ns)
  self.last_output=(0.,0.)
  return self.last_output_ns,0.,0.,self.phase,self.g.fault

class FutureInbox:
 """Bounded cross-topic ordering wait; original receipts never change."""
 def __init__(self):self.items={};self.owners={}
 def offer(self,key,stamp,receipt,payload,clock_ns,now,owner=None):
  if owner is not None:
   if key in self.owners and self.owners[key]!=owner:raise ValueError('pending owner replaced')
   if key not in self.owners and len(self.owners)>=64:raise ValueError('too many source keys')
   self.owners[key]=owner
  ready=self.ready(clock_ns,now)
  if stamp<=clock_ns+25_000_000:ready.append(payload)
  elif key not in self.items:
   if len(self.items)>=64:raise ValueError('future inbox overflow')
   self.items[key]=(stamp,receipt,payload)
  return ready
 def ready(self,clock_ns,now):
  ready=[]
  for key,(stamp,receipt,payload) in list(self.items.items()):
   if now-receipt>.05:raise ValueError('future source did not catch up within50wallms')
   if stamp<=clock_ns+25_000_000:ready.append(payload);del self.items[key]
  return ready
