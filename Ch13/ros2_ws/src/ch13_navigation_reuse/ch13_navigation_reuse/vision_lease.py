"""A camera/target lease whose original capture wall time cannot be renewed."""
import math
class VisionLease:
 def __init__(self):self.sample=None;self.owner=None;self.fault='';self.active=False
 def observe(self,stamp,capture_wall,gid):
  if self.fault:return False
  if self.owner is not None and gid!=self.owner:self.fault='VISION_OWNER_REPLACED';return False
  if type(stamp) is not int or stamp<=0 or not math.isfinite(capture_wall):self.fault='INVALID_VISION_CAPTURE';return False
  self.owner=gid
  if self.sample is not None:
   if stamp<self.sample[0]:self.fault='VISION_REORDER';return False
   if stamp==self.sample[0]:return False
  self.sample=(stamp,capture_wall);return True
 def valid(self,clock,wall):return self.sample is not None and -25_000_000<=clock-self.sample[0]<=300_000_000 and 0<=wall-self.sample[1]<=.3
 def enable(self,clock,wall):
  if self.fault or not self.valid(clock,wall):return False
  self.active=True;return True
 def check(self,clock,wall):
  if self.active and not self.valid(clock,wall):self.fault='VISION_EXPIRED'
  return not self.fault and self.valid(clock,wall)
