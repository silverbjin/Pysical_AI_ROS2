"""Full discrete equilibrium derivative against completed actual-URDF experiment."""
import hashlib,json,sys,uuid,copy,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from independent_contact_model import build
out=Path(sys.argv[1]);manifest=json.loads((out/'manifest.json').read_bytes())
closure=json.loads((out/'closure.json').read_bytes());assert closure['normal_process_return'] and not closure['residual']
data=json.loads((out/'run.stdout').read_bytes());config=json.loads((out/'config.json').read_bytes())
assert len(data['cases'])==25 and data['completed'] and data['ROS_shutdown']
baseline=data['cases'][0];urdf=config['control_urdf'];tree=ET.fromstring(urdf)
pose0=np.eye(4);pose0[:3,3]=baseline['last_body']['position'];pose0[:3,:3]=Rotation.from_quat(baseline['last_body']['orientation']).as_matrix()
fixture={'urdf':urdf,'args':{'joints':baseline['mean_joint_positions'],'body_pose':pose0.tolist(),
 'points':dict(zip(('fr_foot','fl_foot','rr_foot','rl_foot'),[[0.,0.,0.]]*4)),
 'forces_world':dict(zip(('fr_foot','fl_foot','rr_foot','rl_foot'),np.array(baseline['mean_forces_world_flat']).reshape(4,3).tolist()))}}
model=build(fixture,sphere_plane_points=True);names=model['joint_names'];nq=6+len(names);nf=12
q0=np.array([baseline['mean_joint_positions'][n] for n in names]);qcmd=np.array([config['targets'][n] for n in names])
gains=np.array([config['gains'][n] for n in names]);f0=np.array(baseline['mean_forces_world_flat'])
x0=np.r_[np.zeros(6),q0]

def at(x):
 a=copy.deepcopy(fixture);p=pose0.copy();p[:3,3]+=x[:3];p[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@pose0[:3,:3]
 a['args']['body_pose']=p.tolist();a['args']['joints']=dict(zip(names,x[6:]))
 m=build(a,sphere_plane_points=True)
 u=np.r_[np.zeros(6),gains*(qcmd-x[6:])]
 return u-m['gravity']+m['mapped']@f0,m

epsilon=1e-6
grad=np.column_stack([(at(x0+np.eye(nq)[i]*epsilon)[0]-at(x0-np.eye(nq)[i]*epsilon)[0])/(2*epsilon) for i in range(nq)])
matrix=np.block([[grad,model['mapped']],[model['contact'],np.zeros((nf,nf))]])
input_matrix=np.zeros((nq+nf,12))
for column,name in enumerate(data['leg_names']):input_matrix[6+names.index(name),column]=config['gains'][name]
singular=np.linalg.svd(matrix,compute_uv=False);assert singular[-1]>1e-9,('rank-deficient full model',singular[-1])
solution=np.linalg.solve(matrix,-input_matrix);predicted=solution[nq:,:]
delta=data['input_joint_delta_rad']
observed=np.column_stack([(np.array(data['cases'][1+2*i]['mean_forces_world_flat'])-
 np.array(data['cases'][2+2*i]['mean_forces_world_flat']))/(2*delta) for i in range(12)])
relative=np.linalg.norm(observed-predicted,axis=0)/np.maximum(1.,np.linalg.norm(predicted,axis=0))
linear_residual=float(np.max(np.abs(matrix@solution+input_matrix)))
baseline_equilibrium=float(np.max(np.abs(at(x0)[0])))
passed=bool(np.max(relative)<=.05 and linear_residual<1e-6)
result={'scope':'full_equilibrium_derivative_vs_actual_URDF_installed_PD_component_not_G1_C1_G2',
 'passed':passed,'fixed_relative_column_criterion':.05,'max_relative_column_error':float(np.max(relative)),
 'relative_error_by_joint':dict(zip(data['leg_names'],relative.tolist())),
 'predicted_force_derivative_n_per_rad':predicted.tolist(),'observed_force_derivative_n_per_rad':observed.tolist(),
 'linear_solve_residual':linear_residual,'minimum_singular_value':float(singular[-1]),
 'baseline_equilibrium_residual_nm_or_n':baseline_equilibrium,'mass_kg':model['total'],
 'parameters_fitted':False,'body_pose':pose0.tolist(),'joint_names':names,
 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(__file__).resolve().parent.parent/'independent_contact_model.py')},
 'input_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('run.stdout','config.json','manifest.json')},
 'caveats':['Stationary small perturbations at one four-foot posture only; not proof of unloading path, next tripod, ROS timing or C1/G2.',
 'Point contact sticking linearization with actual sphere-plane normal; no runtime force model changed by this analysis.']}
path=out/('analysis-'+str(uuid.uuid4())+'.json');path.write_text(json.dumps(result,indent=2))
print(json.dumps({'path':str(path),**{k:v for k,v in result.items() if k not in ('predicted_force_derivative_n_per_rad','observed_force_derivative_n_per_rad','body_pose','joint_names','input_sha256','source_sha256')}},indent=2))
raise SystemExit(0 if passed else 1)
