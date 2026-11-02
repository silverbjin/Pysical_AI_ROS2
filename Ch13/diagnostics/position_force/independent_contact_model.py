"""Independent URDF energy/Jacobian oracle. Diagnostic only; no robot commands."""
import json,math,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import linprog

def skew(v):
 x,y,z=v
 return np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])

def origin(tag):
 t=np.eye(4)
 if tag is not None:
  t[:3,3]=np.fromstring(tag.get('xyz','0 0 0'),sep=' ')
  t[:3,:3]=Rotation.from_euler('xyz',np.fromstring(tag.get('rpy','0 0 0'),sep=' ')).as_matrix()
 return t

def build(fixture,*,sphere_plane_points=False):
 a=fixture['args'];tree=ET.fromstring(fixture['urdf'])
 joints=tree.findall('joint');parents={j.find('child').get('link'):j for j in joints}
 root=(set(l.get('name') for l in tree.findall('link'))-set(parents)).pop()
 frames={root:np.asarray(a['body_pose'],float)}
 pending=list(joints);ordered=[];joint_origins={};joint_axes={}
 while pending:
  ready=[j for j in pending if j.find('parent').get('link') in frames]
  if not ready:raise ValueError('disconnected/cyclic URDF')
  for j in ready:
   name=j.get('name');kind=j.get('type');child=j.find('child').get('link')
   frame=frames[j.find('parent').get('link')]@origin(j.find('origin'))
   motion=np.eye(4)
   if kind!='fixed':
    axis=np.fromstring(j.find('axis').get('xyz'),sep=' ');axis/=np.linalg.norm(axis)
    joint_origins[name]=frame[:3,3].copy();joint_axes[name]=frame[:3,:3]@axis
    q=a['joints'][name]
    if kind=='prismatic':motion[:3,3]=axis*q
    elif kind in ('revolute','continuous'):motion[:3,:3]=Rotation.from_rotvec(axis*q).as_matrix()
    else:raise ValueError('unknown joint kind')
    ordered.append(j)
   frames[child]=frame@motion;pending.remove(j)
 names=[j.get('name') for j in ordered];index={name:6+i for i,name in enumerate(names)}
 nd=6+len(names);base=frames[root][:3,3]
 def jacobian(link,point):
  linear=np.zeros((3,nd));angular=np.zeros((3,nd))
  linear[:,:3]=np.eye(3);linear[:,3:6]=-skew(point-base);angular[:,3:6]=np.eye(3)
  while link in parents:
   j=parents[link];name=j.get('name')
   if name in index:
    col=index[name];axis=joint_axes[name]
    if j.get('type')=='prismatic':linear[:,col]=axis
    else:
     linear[:,col]=np.cross(axis,point-joint_origins[name]);angular[:,col]=axis
   link=j.find('parent').get('link')
  return linear,angular
 mass=np.zeros((nd,nd));gravity=np.zeros(nd);total=0.
 for link in tree.findall('link'):
  inertial=link.find('inertial')
  if inertial is None:continue
  weight=float(inertial.find('mass').get('value'));total+=weight
  transform=frames[link.get('name')]@origin(inertial.find('origin'))
  v,w=jacobian(link.get('name'),transform[:3,3]);tag=inertial.find('inertia')
  ixx,iyy,izz,ixy,ixz,iyz=[float(tag.get(n)) for n in ('ixx','iyy','izz','ixy','ixz','iyz')]
  tensor=np.array([[ixx,ixy,ixz],[ixy,iyy,iyz],[ixz,iyz,izz]])
  tensor=transform[:3,:3]@tensor@transform[:3,:3].T
  mass+=weight*v.T@v+w.T@tensor@w
  gravity+=weight*v.T@np.array([0.,0.,9.81])
 damping=np.zeros(nd);effort=np.zeros(nd)
 for j in ordered:
  k=index[j.get('name')];dyn=j.find('dynamics')
  damping[k]=float(dyn.get('damping','0')) if dyn is not None else 0.
  effort[k]=float(j.find('limit').get('effort'))
 feet=('fr_foot','fl_foot','rr_foot','rl_foot')
 centers=np.array([frames[foot][:3,3] for foot in feet])
 radii=np.array([float(tree.find(f"link[@name='{foot}']/collision/geometry/sphere").get('radius')) for foot in feet])
 points=centers-np.outer(radii,[0.,0.,1.]) if sphere_plane_points else np.array([a['points'][f] for f in feet])
 contact=np.vstack([jacobian(foot,points[i])[0] for i,foot in enumerate(feet)])
 leg_names=[prefix+'_'+part+'_joint' for prefix in ('fr','fl','rr','rl') for part in ('hip','thigh','calf')]
 leg_indices=[index[n] for n in leg_names]
 gains=np.array([float(tree.find(f"ros2_control/joint[@name='{n}']/param[@name='ch13_kp']").text) for n in leg_names])
 mapped=contact.T+.002*damping[:,None]*np.linalg.solve(mass,contact.T)
 static=gravity-contact.T@np.array([a['forces_world'][f] for f in feet]).ravel()
 command=gravity-mapped@np.array([a['forces_world'][f] for f in feet]).ravel()
 return dict(total=total,mass=mass,gravity=gravity,damping=damping,effort=effort,contact=contact,
  mapped=mapped,static=static,command=command,leg_indices=leg_indices,leg_names=leg_names,gains=gains,
  joint_names=names,feet=feet,body=np.asarray(a['body_pose'],float),points=points,foot_centers=centers)

def response(model):
 k=model['leg_indices'];j=model['contact'][:,k]
 compliance=j@np.diag(1/model['gains'])@model['mapped'][k,:]
 stiffness=np.linalg.solve(compliance,np.eye(12))
 b=np.vstack([np.column_stack((np.eye(3),-skew(p-model['body'][:3,3]))) for p in model['points']])
 # Do not force symmetry on a potentially non-reciprocal discrete response.
 r=-(stiffness-stiffness@b@np.linalg.solve(b.T@stiffness@b,b.T@stiffness))
 return dict(compliance=compliance,response=r,floating_equilibrium_residual=np.max(np.abs(b.T@r)),
  rigid_motion_residual=np.max(np.abs(r@b)),asymmetry=np.max(np.abs(r-r.T)))

def tripod(model,selected):
 # An offline necessary feasibility check at one posture, not a safe path.
 k=model['leg_indices'];root=slice(0,6);mapping=model['mapped'];jac=model['contact'].T
 rows=[];rhs=[]
 for mat in (mapping[k,:],jac[k,:]):
  rows.extend(mat);rhs.extend(model['gravity'][k]+model['effort'][k])
  rows.extend(-mat);rhs.extend(model['effort'][k]-model['gravity'][k])
 tangent=model['body'][:3,0].copy();tangent[2]=0.;tangent/=np.linalg.norm(tangent)
 second=np.cross([0.,0.,1.],tangent)
 for foot in range(4):
  for axis in (tangent,-tangent,second,-second):
   cone=axis.copy();cone[2]-=1/math.sqrt(2);row=np.zeros(12);row[3*foot:3*foot+3]=cone
   rows.append(row);rhs.append(0.)
 bounds=[(None,None)]*12
 for foot in range(4):
  if foot==selected:
   for i in range(3):bounds[3*foot+i]=(0.,0.)
  else:bounds[3*foot+2]=(2.,None)
 result=linprog(np.zeros(12),A_ub=np.asarray(rows),b_ub=np.asarray(rhs),
   A_eq=jac[root,:],b_eq=model['gravity'][root],bounds=bounds,method='highs')
 return {'selected':model['feet'][selected],'status':int(result.status),'feasible':bool(result.success),
  'forces':result.x.reshape(4,3).tolist() if result.success else None,
  'max_inequality_residual':float(np.max(np.asarray(rows)@result.x-np.asarray(rhs))) if result.success else None}

if __name__=='__main__':
 import hashlib,uuid
 repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2')
 fixture=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_d504_infeasible.json'
 f=json.loads(fixture.read_bytes());m=build(f)
 native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
 oracle=json.loads((native/'dart-static-mapping-7d150460-7eab-4ebd-a491-5dc92aa40dd4/evaluate.stdout').read_bytes())
 expected={r['joint']:r['predicted_command_at_zero_velocity_nm'] for r in oracle['rows']}
 error=max(abs(m['command'][i]-expected[n]) for i,n in zip(m['leg_indices'],m['leg_names']))
 assert abs(m['total']-15.2101)<1e-10
 assert np.linalg.eigvalsh(m['mass'])[0]>0.
 assert error<1e-9,('independent versus DART oracle',error)
 out={'scope':'offline_independent_inertia_and_response_candidate_not_runtime_or_acceptance',
  'mass_kg':m['total'],'independent_DART_command_max_error_nm':error,
  'mass_eigen_min':float(np.linalg.eigvalsh(m['mass'])[0]),'mass_symmetry':float(np.max(np.abs(m['mass']-m['mass'].T))),
  'response':{k:(v.tolist() if isinstance(v,np.ndarray) else float(v)) for k,v in response(m).items()},
  'tripod_necessary_checks':[tripod(m,i) for i in range(4)],
  'caveats':['Tripod check is current posture only, zero velocity, no reachability/path/future geometry certification.',
   'Response candidate is not yet validated against actual position perturbations; no runtime change allowed from this alone.'],
  'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
  'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 p=native/('independent-contact-model-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(out,indent=2))
 p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps({'path':str(p),'mass':m['total'],'oracle_error':error,'tripods':out['tripod_necessary_checks'],
 'response_checks':{k:v for k,v in out['response'].items() if k not in ('compliance','response')}},indent=2))
