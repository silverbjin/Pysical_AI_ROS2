"""Closed matrices only, named representation comparisons, no engine/installation."""
import hashlib,json,subprocess,uuid
from pathlib import Path
r=Path.cwd();t=r/'.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO'
b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
s=r/'Ch13/ros2_ws/src/integrated_robot_navigation_sensors'
out=b/('qp-formulation-'+str(uuid.uuid4()));out.mkdir()
source=t/'qp-formulation-diagnostic.cpp';(out/source.name).write_bytes(source.read_bytes())
command=['c++','-std=c++17','-O2',str(source),'-I'+str(s/'include'),
         '-I'+str(s/'third_party/qpmad/include'),'-I/usr/include/eigen3','-o',str(out/'probe')]
with (out/'build.log').open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
result={'scope':'offline_representations_not_runtime_retry_or_acceptance','command':command,'sources':{},'cases':[]}
for p in (source,s/'include/integrated_robot_navigation_sensors/fixed_coordinate_qp.hpp',s/'include/integrated_robot_navigation_sensors/box_presolve.hpp'):
 result['sources'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('job72-qp-diagnostic-bc0ea286-2a78-4644-a890-f17bf750e5eb',
             'job130-qp-diagnostic-2c2471e8-b4e1-4bfa-a5da-bf2b2b38967d'):
 p=b/name/'problem.json';reply=subprocess.run([str(out/'probe'),str(p)],capture_output=True,text=True,check=True)
 result['cases'].append({'input':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'representations':json.loads(reply.stdout)})
(out/'method.py').write_bytes(Path(__file__).read_bytes());(out/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'path':str(out),'cases':[{**c,'representations':[{k:v for k,v in x.items() if k!='primal'} for x in c['representations']]} for c in result['cases']]}))
