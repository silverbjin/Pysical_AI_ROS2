"""Actuation-aware necessary tripod conditions, not a closed-loop/path PASS."""
import copy,hashlib,json,math,sys,uuid
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from independent_contact_model import build
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.leg_kinematics import ik_leg
from integrated_robot_navigation.support import support_margin

repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2')
fixture=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_d504_infeasible.json'
f=json.loads(fixture.read_bytes());robot=compile_model(f['urdf']);foot=f['args']['foot'];selected=robot.feet.index(foot)
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')

def solve(m,*,discrete=True):
 j=m['contact'].T;mapping=m['mapped'] if discrete else j
 actuated=list(range(6,m['mass'].shape[0]));rows=[];rhs=[]
 for i in actuated:
  rows.extend([np.r_[mapping[i],-m['effort'][i]],np.r_[-mapping[i],-m['effort'][i]]])
  rhs.extend([m['gravity'][i],-m['gravity'][i]])
  rows.extend([np.r_[j[i],0.],np.r_[-j[i],0.]])
  rhs.extend([m['gravity'][i]+m['effort'][i],m['effort'][i]-m['gravity'][i]])
 tangent=m['body'][:3,0].copy();tangent[2]=0.;tangent/=np.linalg.norm(tangent);second=np.cross([0.,0.,1.],tangent)
 for k in range(4):
  for axis in (tangent,-tangent,second,-second):
   row=np.zeros(13);row[3*k:3*k+3]=axis;row[3*k+2]-=1/math.sqrt(2)
   rows.append(row);rhs.append(0.)
 bounds=[(None,None)]*12+[(0.,1.)]
 for k in range(4):
  if k==selected:
   for a in range(3):bounds[3*k+a]=(0.,0.)
  else:bounds[3*k+2]=(2.,None)
 objective=np.r_[np.zeros(12),1.]
 result=linprog(objective,A_ub=np.array(rows),b_ub=np.array(rhs),
  A_eq=np.column_stack([j[:6],np.zeros(6)]),b_eq=m['gravity'][:6],bounds=bounds,method='highs')
 out={'feasible':bool(result.success),'solver_status':int(result.status)}
 if result.success:
  forces=result.x[:12];u=m['gravity']-mapping@forces;tau=m['gravity']-j@forces
  com=np.r_[m['body'][:2,3]+np.array([-m['gravity'][4],m['gravity'][3]])/(m['total']*9.81),0.]
  points=[f['args']['points'][name] for name in robot.feet if name!=foot]
  margin=support_margin(com,points)
  out.update(max_command_effort_ratio=float(result.x[-1]),min_command_effort_margin=float(np.min(m['effort'][6:]-np.abs(u[6:]))),
   inequality_residual=float(np.max(np.array(rows)@result.x-np.array(rhs))),
   equilibrium_residual=float(np.max(np.abs(j[:6]@forces-m['gravity'][:6]))),
   forces_world=forces.reshape(4,3).tolist(),command_effort=dict(zip(m['joint_names'],u[6:].tolist())),
   continuous_effort=dict(zip(m['joint_names'],tau[6:].tolist())),support_margin_m=float(margin),
   support_margin_required_m=f['limits']['min_support_margin_m'],support_margin_passed=bool(margin>=f['limits']['min_support_margin_m']))
 return out

baseline=build(f);continuous=solve(baseline,discrete=False);current=solve(baseline)
rows=[{'phase':'current_posture_selected_contact_zero','discrete':current}]
start=baseline['foot_centers'][selected].copy();end=np.array(f['args']['future_targets'][foot]);end[2]=start[2]
assert np.linalg.norm(end[:2]-start[:2])<=f['limits']['max_foot_displacement_m']
names=[foot[:2]+'_'+part+'_joint' for part in ('hip','thigh','calf')]
for fraction in (.2,.35,.5,.65,.8):
 candidate=copy.deepcopy(f);target=start*(1-fraction)+end*fraction
 target[2]+=f['limits']['swing_height_m']*math.sin(math.pi*fraction)
 pose=np.asarray(f['args']['body_pose']);local=np.linalg.solve(pose,np.r_[target,1.])[:3]
 q=ik_leg(robot,foot,local,tuple(f['args']['joints'][n] for n in names))
 for n,v in zip(names,q):candidate['args']['joints'][n]=v
 gait_bounds=all(f['limits']['gait_joint_bounds'][part][0]<=v<=f['limits']['gait_joint_bounds'][part][1] for part,v in zip(('hip','thigh','calf'),q))
 m=build(candidate);rows.append({'phase':'aerial_necessary_sample','fraction':fraction,'world_foot_center':target.tolist(),
  'selected_ik':list(q),'gait_joint_bounds_passed':gait_bounds,'discrete':solve(m)})
out={'scope':'next_tripod_actuation_necessary_conditions_not_path_or_C1_G2_acceptance','selected':foot,
 'all20actuator_caps_included':True,'original_friction_cone_and_min_support_force_retained':True,
 'continuous_only_current_posture':continuous,'rows':rows,
 'all_sampled_torque_conditions_feasible':all(r['discrete']['feasible'] for r in rows),
 'all_sampled_support_margins_passed':all(r['discrete'].get('support_margin_passed',False) for r in rows),
 'caveats':['Finite posture samples and necessary LP only, not full trajectory, nonlinear reachability, collision, tracking or unload timing proof.',
  'Arm actuation bounds included; fixed arm command tracking and measured carry hold still require the real owner.',
  'Failure267 under prior local QP constraints remains failed; no retry or relabeling.'],
 'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
p=root/('discrete-tripod-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(out,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),'continuous_ratio':continuous.get('max_command_effort_ratio'),
 'all_torque_feasible':out['all_sampled_torque_conditions_feasible'],'all_support_margins':out['all_sampled_support_margins_passed'],
 'rows':[{'phase':r['phase'],'fraction':r.get('fraction'),'feasible':r['discrete']['feasible'],
 'max_ratio':r['discrete'].get('max_command_effort_ratio'),'margin':r['discrete'].get('support_margin_m'),
 'effort_margin':r['discrete'].get('min_command_effort_margin')} for r in rows]},indent=2))
