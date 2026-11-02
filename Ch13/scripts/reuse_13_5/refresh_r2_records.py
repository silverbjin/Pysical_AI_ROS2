"""Refresh exact-byte source/evidence manifests without changing gate values."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
lockpath=root/'Ch13/dependencies/section_13_5_reuse.lock.json'
lock=json.loads(lockpath.read_text(encoding='utf-8'))
paths=[]
for name in ['ch13_navigation_reuse','ch13_reuse_wire']:
 for p in (root/'Ch13/ros2_ws/src'/name).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:paths.append(p)
def entry(p,relative):
 b=p.read_bytes();return {'path':p.relative_to(relative).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
current=[entry(p,root) for p in sorted(paths)]
if lock.get('acceptance',{}).get('R3')=='NOT_STARTED':lock['r2']['source_files']=current
else:lock.setdefault('r3',{})['source_files']=current
lock['current_source_files']=current
lockpath.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
evidence=root/'Ch13/evidence/section_13_5_reuse';manifest=evidence/'evidence_manifest.json'
m=json.loads(manifest.read_text(encoding='utf-8'))
m['files']=[entry(p,evidence) for p in sorted(evidence.rglob('*')) if p.is_file() and p!=manifest and '__pycache__' not in p.parts]
manifest.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
print('manifest source/evidence',len(current),len(m['files']))
