"""Native ROS camera samples bound to C++ actual GID/first receipt by SHA256."""
import hashlib,math,struct,time
KINDS={'rgb','depth','camera_info','camera_meta'}
def canonical(kind,m):
 def u(v):return struct.pack('<I',int(v))
 def text(v):
  b=v.encode('utf-8')
  if len(b)>2048:raise ValueError('camera string bound')
  return u(len(b))+b
 if kind=='camera_meta':return text(m.data)
 h=m.header;b=struct.pack('<iI',h.stamp.sec,h.stamp.nanosec)+text(h.frame_id)+u(m.height)+u(m.width)
 if kind in ('rgb','depth'):
  if len(m.data)>524288:raise ValueError('camera image bound')
  return b+text(m.encoding)+bytes([m.is_bigendian])+u(m.step)+u(len(m.data))+bytes(m.data)
 if kind!='camera_info' or len(m.d)>64:raise ValueError('camera calibration kind/bound')
 doubles=lambda a:struct.pack('<'+'d'*len(a),*a)
 return b+text(m.distortion_model)+u(len(m.d))+doubles(m.d)+doubles(m.k)+doubles(m.r)+doubles(m.p)+u(m.binning_x)+u(m.binning_y)+u(m.roi.x_offset)+u(m.roi.y_offset)+u(m.roi.height)+u(m.roi.width)+bytes([int(m.roi.do_rectify)])
class CameraLink:
 def __init__(self):self.payloads={};self.receipts={};self.delivered={};self.owners={};self.relay=None
 def trim(self,m,n=16):
  while len(m)>n:m.pop(next(iter(m)))
 def native(self,kind,message):
  if kind not in KINDS:raise ValueError('camera native kind')
  b=canonical(kind,message);key=(kind,hashlib.sha256(b).hexdigest())
  if key in self.delivered:return None
  self.payloads.setdefault(key,(message,len(b),time.monotonic()));self.trim(self.payloads);return self.match(key)
 def receipt(self,packet):
  if len(packet)>1024:raise ValueError('camera metadata bound')
  version,kind,gid,relay,receipt_ns,source_ns,digest,size=packet.split('|')
  if version!='camera1' or kind not in KINDS or len(gid)!=32 or len(relay)!=32 or len(digest)!=64:raise ValueError('camera metadata schema')
  gidbytes=bytes.fromhex(gid);bytes.fromhex(relay);bytes.fromhex(digest);wall=int(receipt_ns)/1e9;size=int(size)
  if not math.isfinite(wall) or wall>time.monotonic()+.01 or wall<0 or not 0<size<=524288:raise ValueError('camera receipt time/size')
  if self.relay is not None and self.relay!=relay:raise ValueError('camera relay replaced')
  if kind in self.owners and self.owners[kind]!=gid:raise ValueError('camera source owner replaced:'+kind)
  self.relay=relay;self.owners[kind]=gid;key=(kind,digest)
  if key in self.delivered:return None
  self.receipts.setdefault(key,{'publisher_gid':gidbytes,'relay_gid':relay,'receipt_wall':wall,'source_timestamp':int(source_ns),'canonical_sha256':digest,'canonical_bytes':size});self.trim(self.receipts);return self.match(key)
 def match(self,key):
  if key not in self.payloads or key not in self.receipts:return None
  message,size,native_wall=self.payloads.pop(key);info=self.receipts.pop(key)
  if size!=info['canonical_bytes']:raise ValueError('camera canonical size mismatch')
  info['native_receipt_wall']=native_wall;self.delivered[key]=True;self.trim(self.delivered,64);return key[0],message,info
