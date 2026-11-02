"""Closed exact matrices and independent Farkas proof; never installed."""
import hashlib,json,subprocess,uuid
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from integrated_robot_navigation import native_xyz
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.model import compile_model

r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
out=b/('infeasible-264-'+str(uuid.uuid4()));out.mkdir()
s=r/'Ch13/ros2_ws/src/integrated_robot_navigation_sensors'
install=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/install/integrated_robot_navigation_sensors')
source=(s/'src/xyz_optimizer.cpp').read_text()
needle='auto status=p.solver.solve(y,problem.h,problem.g,problem.lo,problem.hi,\n      problem.a,alb,problem.b,parameters());mark(2);'
assert source.count(needle)==1
capture='''auto as_json=[](const M & value) {nlohmann::json out=nlohmann::json::array();
for(Eigen::Index r=0;r<value.rows();++r) {nlohmann::json row=nlohmann::json::array();
for(Eigen::Index c=0;c<value.cols();++c) {row.push_back(value(r,c));}out.push_back(row);}return out;};
nlohmann::json dump={{"a",as_json(rows)},{"b",as_json(rhs)},
{"lo",as_json(lo)},{"hi",as_json(hi)},{"h",as_json(h)},{"g",as_json(linear)}};
std::ofstream("'''+str(out/'problem.json')+'''")<<dump.dump();
'''
debug=out/'debug.cpp';debug.write_text('#include <fstream>\n'+source.replace(needle,capture+needle))
(out/'lib').mkdir();metadata=out/'share/integrated_robot_navigation_sensors/third_party/qpmad';metadata.mkdir(parents=True)
for name in ('UPSTREAM.json','LICENSE','NOTICE'):(metadata/name).write_bytes((s/'third_party/qpmad'/name).read_bytes())
library=out/'lib/libnavigation_xyz_optimizer.so'
command=['c++','-std=c++17','-O2','-fPIC','-shared',str(debug),'-I'+str(s/'include'),
 '-I'+str(s/'third_party/qpmad/include'),'-I/usr/include/eigen3','-L'+str(install/'lib'),
 '-lnavigation_mass_kinematics','-lnavigation_reference_geometry','-Wl,-rpath,'+str(install/'lib'),'-o',str(library)]
with (out/'build.log').open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
fixture=r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_ab85_infeasible.json'
c=json.loads(fixture.read_bytes());m=compile_model(c['urdf']);old=native_xyz.optimizer_library_path
native_xyz.optimizer_library_path=lambda:library;error=None
try:
 with NativeMassEvaluator(m) as mass:
  k=CompleteXYZTransition(m,c['limits'],native_mass=mass)
  try:k.prepare();k.step(**c['args'])
  except ValueError as e:error=str(e)
  finally:k.close()
finally:native_xyz.optimizer_library_path=old
p=json.loads((out/'problem.json').read_bytes());a=np.asarray(p['a']);v=np.asarray(p['b']).ravel()
lo=np.asarray(p['lo']).ravel();hi=np.asarray(p['hi']).ravel();feet=m.feet
def label(i):
 if i<68:
  leg,k=divmod(i,17)
  if k<5:return f'{feet[leg]}:'+('normal' if k==0 else f'friction{k}')
  joint,k=divmod(k-5,4)
  return f'{feet[leg]}:{("hip","thigh","calf")[joint]}:{("static+","servo+","static-","servo-")[k]}'
 if i<100:return f'{feet[(i-68)//8]}:stepL1:{(i-68)%8}'
 return f'{feet[(i-100)//8]}:totalL1:{(i-100)%8}'
labels=[label(i) for i in range(len(v))]
aa=np.vstack((a,np.eye(12),-np.eye(12)));bb=np.r_[v,hi,-lo]
labels += [f'upper[{i}]' for i in range(12)]+[f'lower[{i}]' for i in range(12)]
norm=np.maximum(np.linalg.norm(aa,axis=1),1e-12);na=aa/norm[:,None];nb=bb/norm
lp=linprog(np.zeros(12),A_ub=na,b_ub=nb,bounds=[(None,None)]*12,method='highs')
dual=linprog(np.ones(len(nb)),A_eq=np.vstack((na.T,nb)),b_eq=np.r_[np.zeros(12),-1.],bounds=(0.,None),method='highs')
certificate=None
if dual.success:
 certificate={'aT_y_max':float(np.max(np.abs(na.T@dual.x))),'bT_y':float(nb@dual.x),
 'nonnegative_min':float(np.min(dual.x)),
 'rows':[{'row':i,'constraint':labels[i],'weight':float(z),'scaled_rhs':float(nb[i])} for i,z in enumerate(dual.x) if z>1e-7]}
groups={}
for group,selection in [('without_servo',[i for i in range(len(nb)) if 'servo' not in labels[i]]),
 ('without_static',[i for i in range(len(nb)) if 'static' not in labels[i]]),
 ('without_friction',[i for i in range(len(nb)) if 'friction' not in labels[i]])]:
 q=linprog(np.zeros(12),A_ub=na[selection],b_ub=nb[selection],bounds=[(None,None)]*12,method='highs')
 groups[group]={'success':bool(q.success),'status':int(q.status)}
result={'scope':'offline_feasibility_proof_not_runtime_relaxation_or_physical_acceptance',
 'native_error':error,'lp':{'success':bool(lp.success),'status':int(lp.status),'message':lp.message},
 'certificate':certificate,'counterfactual_constraint_groups':groups,'command':command,
 'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
 'source_sha256':hashlib.sha256(debug.read_bytes()).hexdigest(),'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest()}
(out/'result.json').write_text(json.dumps(result,indent=2));(out/'method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(out),'result':result},indent=2))
