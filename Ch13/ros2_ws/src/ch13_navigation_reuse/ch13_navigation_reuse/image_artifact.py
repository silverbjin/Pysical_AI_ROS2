"""Small lossless RGB artifact codec for retained simulator evidence."""
import struct,zlib,numpy as np

def write_rgb(path,rgb):
 h,w,c=rgb.shape
 if c!=3:raise ValueError('RGB required')
 def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in rgb)))+chunk(b'IEND',b''))

def read_rgb(path):
 raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';i=8;payload=b''
 while i<len(raw):
  size=struct.unpack('!I',raw[i:i+4])[0];kind=raw[i+4:i+8];data=raw[i+8:i+8+size];assert zlib.crc32(kind+data)&0xffffffff==struct.unpack('!I',raw[i+8+size:i+12+size])[0]
  if kind==b'IHDR':w,h,bits,color,_,_,_=struct.unpack('!2I5B',data);assert (w,h,bits,color)==(320,240,8,2)
  if kind==b'IDAT':payload+=data
  i+=12+size
 decoded=np.frombuffer(zlib.decompress(payload),dtype=np.uint8).reshape(h,w*3+1);assert not decoded[:,0].any();return decoded[:,1:].reshape(h,w,3).copy()
