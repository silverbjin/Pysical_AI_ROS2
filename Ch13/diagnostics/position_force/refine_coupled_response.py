"""Differentiate full discrete equilibrium; no new simulator run or fitted gains."""
import hashlib,json,uuid
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from independent_contact_model import skew
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
source=root/'coupled-position-probe-a2277a36-5a2e-4998-97de-0d583ddc115e/run.stdout'
d=json.loads(source.read_bytes());cases=d['conditions'];baseline=cases[0]
offsets=np.array([[.25,-.15,-.2],[.25,.15,-.2],[-.25,-.15,-.2],[-.25,.15,-.2]])
nd=10;damp=np.r_[np.zeros(6),np.ones(4)*d['damping_ns_per_m']]
q0=np.array(baseline['mean_position_m']);f0=np.zeros((4,3));f0[:,2]=baseline['mean_force_z_n']
x0=np.r_[0.,0.,.22-np.mean(q0),0.,0.,0.,q0,f0.ravel()]
kp=d['kp_n_per_m'];h=d['physics_dt_s'];radius=.02

def parts(x):
 t=x[:3];rotation=Rotation.from_rotvec(x[3:6]).as_matrix();q=x[6:10]
 mass=np.zeros((nd,nd));gravity=np.zeros(nd);contact=[];centers=[]
 mass[:3,:3]=np.eye(3)*d['trunk_mass_kg']
 mass[3:6,3:6]=rotation@np.diag([.02,.03,.04])@rotation.T
 gravity[2]=d['trunk_mass_kg']*9.81
 for i in range(4):
  point=t+rotation@(offsets[i]+np.array([0.,0.,q[i]]));centers.append(point)
  j=np.zeros((3,nd));j[:,:3]=np.eye(3);j[:,3:6]=-skew(point-t);j[:,6+i]=rotation[:,2]
  angular=np.zeros((3,nd));angular[:,3:6]=np.eye(3)
  mass+=d['foot_mass_kg']*j.T@j+angular.T@(np.eye(3)*.000016)@angular
  gravity+=d['foot_mass_kg']*j.T@np.array([0.,0.,9.81])
  # Sphere contact geometry follows its world normal, not a frozen material
  # point. Instantaneous sticking uses this current point Jacobian.
  pcontact=point-np.array([0.,0.,radius])
  jc=j.copy();jc[:,3:6]=-skew(pcontact-t);contact.append(jc)
 return mass,gravity,np.vstack(contact),np.array(centers)

mass,gravity,j0,centers=parts(x0)
def equilibrium(x):
 m,g,j,_=parts(x);u=np.r_[np.zeros(6),kp*(np.array(baseline['target_m'])-x[6:10])]
 mapping=j.T+h*damp[:,None]*np.linalg.solve(m,j.T)
 return u-g+mapping@x[10:]

# Differentiate equilibrium; contact constraints use the exact instantaneous
# sticking Jacobian (not a fake stationary sphere-center constraint).
epsilon=1e-6
gradient=np.column_stack([(equilibrium(x0+np.eye(22)[i]*epsilon)-
 equilibrium(x0-np.eye(22)[i]*epsilon))/(2*epsilon) for i in range(22)])
matrix=np.vstack([gradient,np.column_stack((j0,np.zeros((12,12))))])
input_matrix=np.zeros((22,4));input_matrix[6:10,:]=np.eye(4)*kp
solution,residual,rank,singular=np.linalg.lstsq(matrix,-input_matrix,rcond=1e-11)
predicted=solution[10:,:].reshape(4,3,4)[:,2,:]
observed=np.column_stack([(np.array(cases[1+2*i]['mean_force_z_n'])-
 np.array(cases[2+2*i]['mean_force_z_n']))/(2*d['input_delta_m']) for i in range(4)])
error=float(np.max(np.abs(predicted-observed))/np.max(np.abs(predicted)))
linear_residual=float(np.max(np.abs(matrix@solution+input_matrix)))
out={'scope':'offline_full_equilibrium_derivative_against_completed_coupled_probe_not_robot_acceptance',
 'previous_constant_geometry_relative_error':.04867527836746428,
 'refined_predicted_derivative_n_per_m':predicted.tolist(),'observed_derivative_n_per_m':observed.tolist(),
 'relative_max_error':error,'linear_residual':linear_residual,'rank':int(rank),
 'equilibrium_baseline_residual':float(np.max(np.abs(equilibrium(x0)))),
 'fixed_criterion_relative_error':.02,'passed':bool(error<=.02 and linear_residual<1e-7),
 'parameters_fitted':False,'changes':'Include gravity, contact geometry, mass and implicit mapping derivatives; actual sphere normal and sticking Jacobian distinguished.',
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'caveat':'Analysis of completed known reduced model only. Actual robot12axis response and runtime budget remain unvalidated.'}
p=root/('coupled-response-refinement-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(out,indent=2))
p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),**out},indent=2))
raise SystemExit(0 if out['passed'] else 1)
