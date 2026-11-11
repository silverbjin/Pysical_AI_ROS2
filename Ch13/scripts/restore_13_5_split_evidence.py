import bisect,hashlib,io,json,zipfile,sys
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
parts=sorted(base.glob('task8-preflight-pair-g2-mujoco-22afb6c3-*.zip.part[0-9][0-9][0-9]'))
assert len(parts)==8
class Parts(io.RawIOBase):
 def __init__(self):
  self.fs=[p.open('rb') for p in parts];self.starts=[0]
  for p in parts:self.starts.append(self.starts[-1]+p.stat().st_size)
  self.pos=0
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.starts[-1]+offset
  if self.pos<0:raise ValueError('negative seek')
  return self.pos
 def read(self,size=-1):
  if size<0:size=self.starts[-1]-self.pos
  chunks=[]
  while size>0 and self.pos<self.starts[-1]:
   i=bisect.bisect_right(self.starts,self.pos)-1; f=self.fs[i];f.seek(self.pos-self.starts[i]); n=min(size,self.starts[i+1]-self.pos); b=f.read(n)
   if not b:raise OSError('unexpected end')
   chunks.append(b);self.pos+=len(b);size-=len(b)
  return b''.join(chunks)
 def close(self):
  for f in self.fs:f.close()
  super().close()
def sha(stream):
 h=hashlib.sha256()
 for b in iter(lambda:stream.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
ledger=json.loads((base.parent/'retention_duplicate_cleanup_20261111.json').read_text(encoding='utf-8'))
destination=Path(sys.argv[1]).resolve(strict=True)
assert destination.is_dir()
with Parts() as stream:
 assert sha(stream)==ledger['archive_sha256']
 stream.seek(0)
 with zipfile.ZipFile(stream) as archive:
  for row in ledger['removed']:
   member=archive.getinfo(row['member']);target=destination/Path(member.filename).name
   with archive.open(member) as source,target.open('xb') as output:
    h=hashlib.sha256()
    for block in iter(lambda:source.read(4*1024*1024),b''):
     h.update(block);output.write(block)
   assert target.stat().st_size==row['bytes'] and h.hexdigest()==row['sha256'],str(target)
   print('restored',target,row['sha256'])
