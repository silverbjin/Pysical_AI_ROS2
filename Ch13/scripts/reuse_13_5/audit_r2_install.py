"""Audit actual installed Python/data/binary bytes before a physical replay."""
from pathlib import Path
import hashlib,importlib,json,sys,subprocess,os
from ament_index_python.packages import get_package_share_directory,get_package_prefix
root=Path(__file__).resolve().parents[3]
source=root/'Ch13/ros2_ws/src/ch13_navigation_reuse/ch13_navigation_reuse'
share=Path(get_package_share_directory('ch13_navigation_reuse'))
rows=[]
for p in source.glob('*.py'):
 mod=importlib.import_module('ch13_navigation_reuse.'+p.stem) if p.stem!='__init__' else importlib.import_module('ch13_navigation_reuse')
 actual=Path(mod.__file__);expected=hashlib.sha256(p.read_bytes()).hexdigest();found=hashlib.sha256(actual.read_bytes()).hexdigest()
 assert '/install/' in str(actual) and expected==found,(p,actual)
 rows.append({'source':str(p),'installed':str(actual),'sha256':found})
pairs=[(root/'Ch13/scripts/reuse_13_5/reproduce_upstream.py',share/'upstream_corrections/reproduce_upstream.py')]
pairs += [(p,share/folder/p.name) for folder in ['config','launch'] for p in (source.parent/folder).glob('*') if p.is_file()]
for p,installed in pairs:
 assert p.read_bytes()==installed.read_bytes();rows.append({'source':str(p),'installed':str(installed),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
prefix=Path(get_package_prefix('ch13_reuse_wire'));a=prefix.parents[1]/'build/ch13_reuse_wire/ingress';b=prefix/'lib/ch13_reuse_wire/ingress'
sections={}
for section in ['.text','.rodata']:
 x=subprocess.check_output(['objcopy','-O','binary','--only-section='+section,str(a),'/dev/stdout'])
 y=subprocess.check_output(['objcopy','-O','binary','--only-section='+section,str(b),'/dev/stdout'])
 assert x==y,'installed ELF code/rodata differs'
 sections[section]=hashlib.sha256(y).hexdigest()
# CMake removes build RPATH at install; whole ELF hashes may differ legitimately.
rows.append({'elf_relocation':'CMake install RPATH change','build_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'installed_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'matching_sections':sections})
rows.append({'source':'compiled ch13_reuse_wire ingress','installed':str(b),'sha256':hashlib.sha256(b.read_bytes()).hexdigest()})
lock=json.loads((root/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text());up=root.parent/'upstream-iit-locomanipulation-d010212'
assert all(hashlib.sha256((up/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in lock['files'])
legacy=root/'Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision'
for name in ['__init__','contracts','geometry']:
 module=importlib.import_module('integrated_robot_vision'+('' if name=='__init__' else '.'+name));actual=Path(module.__file__);source_legacy=legacy/(name+'.py')
 assert '/install/' in str(actual) and actual.read_bytes()==source_legacy.read_bytes()
 rows.append({'legacy_geometry_source':str(source_legacy),'installed':str(actual),'sha256':hashlib.sha256(actual.read_bytes()).hexdigest()})
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'result':'PASS','upstream_files':len(lock['files']),'installed':rows},indent=2)+'\n');print('INSTALL_AUDIT_PASS',len(rows),'installed artifacts; original94 hashes match')
