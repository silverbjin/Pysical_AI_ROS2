"""Closed exact-job diagnostic build; never installed or used by an engine."""
import hashlib,json,subprocess,uuid
from pathlib import Path
import numpy as np
from scipy.optimize import Bounds,LinearConstraint,minimize
from integrated_robot_navigation import native_xyz
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.model import compile_model

repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
root=base/('job130-qp-diagnostic-'+str(uuid.uuid4()));root.mkdir()
sensor=repo/'Ch13/ros2_ws/src/integrated_robot_navigation_sensors'
install=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/install/integrated_robot_navigation_sensors')
source=(sensor/'src/xyz_optimizer.cpp').read_text();needle='auto status=p.solver.solve(x,h,linear,solver_bounds.first,solver_bounds.second,\n      reduced,alb,reduced_rhs,parameters());mark(2);'
if source.count(needle)!=1:raise RuntimeError('diagnostic source boundary changed')
capture='''auto as_json=[](const M & value) {nlohmann::json out=nlohmann::json::array();
for(Eigen::Index r=0;r<value.rows();++r) {nlohmann::json row=nlohmann::json::array();
for(Eigen::Index c=0;c<value.cols();++c) {row.push_back(value(r,c));}out.push_back(row);}return out;};
nlohmann::json problem={{"h",as_json(h)},{"g",as_json(linear)},{"lower",as_json(lo)},
{"upper",as_json(hi)},{"a_original",as_json(rows)},{"b_original",as_json(rhs)},
{"retained_rows",keep},{"a_reduced",as_json(reduced)},{"b_reduced",as_json(reduced_rhs)}};
'''+needle+'''
problem["status"]=int(status);problem["iterations"]=p.solver.getNumberOfInequalityIterations();
problem["primal"]=as_json(x);problem["original_residual"]=(rows*x-rhs).maxCoeff();
std::ofstream("'''+str(root/'problem.json')+'''")<<problem.dump();
'''
debug=root/'debug.cpp';debug.write_text('#include <fstream>\n'+source.replace(needle,capture))
(root/'lib').mkdir();metadata=root/'share/integrated_robot_navigation_sensors/third_party/qpmad';metadata.mkdir(parents=True)
for name in ('UPSTREAM.json','LICENSE','NOTICE'):
 (metadata/name).write_bytes((sensor/'third_party/qpmad'/name).read_bytes())
library=root/'lib/libnavigation_xyz_optimizer.so'
command=['c++','-std=c++17','-O2','-fPIC','-shared',str(debug),'-I'+str(sensor/'include'),
 '-I'+str(sensor/'third_party/qpmad/include'),'-I/usr/include/eigen3','-L'+str(install/'lib'),
 '-lnavigation_mass_kinematics','-lnavigation_reference_geometry','-Wl,-rpath,'+str(install/'lib'),'-o',str(library)]
with (root/'build.log').open('x') as stream:subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True)
fixture=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_48d0_xyz_iterations.json'
case=json.loads(fixture.read_bytes());model=compile_model(case['urdf']);old=native_xyz.optimizer_library_path
native_xyz.optimizer_library_path=lambda:library
error=None
try:
 with NativeMassEvaluator(model) as mass:
  value=CompleteXYZTransition(model,case['limits'],native_mass=mass)
  try:value.prepare();value.step(**case['args'])
  except ValueError as failed:error=str(failed)
  finally:value.close()
finally:native_xyz.optimizer_library_path=old
problem=json.loads((root/'problem.json').read_bytes())
h=np.asarray(problem['h']);g=np.asarray(problem['g']).ravel();a=np.asarray(problem['a_original']);b=np.asarray(problem['b_original']).ravel()
lo=np.asarray(problem['lower']).ravel();hi=np.asarray(problem['upper']).ravel();primal=np.asarray(problem['primal']).ravel()
objective=lambda x:float(.5*x@h@x+g@x)
# Independent OFFLINE oracle only: no32-iteration/time claim or motor output.
oracle=minimize(objective,np.clip(np.zeros(12),lo,hi),jac=lambda x:h@x+g,method='SLSQP',
 bounds=Bounds(lo,hi),constraints=[LinearConstraint(a,-np.inf,b)],options=dict(maxiter=512,ftol=1e-12))
result=dict(scope='offline_diagnostic_not_runtime_or_physical_acceptance',error=error,
 native_status=problem['status'],native_iterations=problem['iterations'],original_rows=len(b),retained_rows=len(problem['retained_rows']),
 native_original_residual=problem['original_residual'],native_objective=objective(primal),
 oracle=dict(success=bool(oracle.success),status=int(oracle.status),message=str(oracle.message),iterations=int(oracle.nit),
  original_residual=float(np.max(a@oracle.x-b)),objective=objective(oracle.x),primal=oracle.x.tolist()),
 command=command,source_sha256=hashlib.sha256(debug.read_bytes()).hexdigest(),
 library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
with (root/'result.json').open('x') as stream:json.dump(result,stream,indent=2)
(root/'method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(root=str(root),result=result),indent=2))
