"""Offline split-stage diagnosis; never a command or production time proof."""
import hashlib,json,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_xyz import NativeXYZTransition
from integrated_robot_navigation.contact_equilibrium import leg_jacobian_local
from integrated_robot_navigation.leg_kinematics import fk_leg,_leg_spec
r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
fp=r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_1a62_nonlinear_servo.json'
c=json.loads(fp.read_bytes());assert c['provenance']['failed_job_id']==121
m=compile_model(c['urdf']);a=c['args'];feet=m.feet;rows=[]
with NativeMassEvaluator(m) as mass:
 value=NativeXYZTransition(m,c['limits'],terms_evaluator=mass.contact_terms,force_objective='bounded_terminal_force')
 try:
  value.prepare();jac,gravity=mass.contact_terms(m,a['joints'],a['body_pose'],a['points'])
  command=a['command_joints'];pose=np.asarray(a['body_pose']);ref=np.asarray(a['reference_pose'])
  values=np.r_[[a['joints'][n] for n in value._optimizer.names],[command[n] for n in value._optimizer.names],
    pose.ravel(),ref.ravel(),np.asarray([a['points'][f] for f in feet]).ravel(),
    np.asarray([a['forces_world'][f] for f in feet]).ravel(),np.asarray([a['target_forces'].get(f,[0.,0.,0.]) for f in feet]).ravel(),
    np.asarray([a['reference_xyz'][f] for f in feet]).ravel(),np.asarray([a['origins'][f] for f in feet]).ravel(),
    np.asarray([a['allowed_z'][f] for f in feet]).ravel(),np.asarray([jac[f] for f in feet]).ravel(),
    np.asarray([gravity[f] for f in feet]).ravel(),a['dt'],a['speed'],a['min_force']]
  result=value._optimizer.solve(values,feet.index(a['foot']));delta=result[:12].reshape(4,3)
  proposed={f:np.asarray(a['reference_xyz'][f])+delta[i] for i,f in enumerate(feet)}
  exact,clear,bounds=value.geometry.evaluate(joints=a['joints'],body=ref,targets=proposed,
    envelope=a['allowed_z'],selected=a['foot'],future_targets=a['future_targets'])
  for i,f in enumerate(feet):
   hip,offset,upper,lower,names=_leg_spec(m.urdf,f);q=np.array([command[n] for n in names]);point=fk_leg(m,f,q)
   j=leg_jacobian_local(m,f,q,point);dq=np.linalg.solve(j,ref[:3,:3].T@delta[i])
   origin=ref[:3,:3]@point+ref[:3,3];e=np.asarray(a['reference_xyz'][f])-origin
   for k,n in enumerate(names):
    gain=value.gains[n];linear=gain*(q[k]+dq[k]-a['joints'][n]);actual=gain*(exact[n]-a['joints'][n])
    rows.append({'foot':f,'joint':n,'limit_nm':m.limits[n][3],'linear_servo_nm':linear,
     'exact_servo_nm':actual,'excess_nm':abs(actual)-m.limits[n][3],
     'joint_remainder_rad':exact[n]-q[k]-dq[k], 'reference_origin_error_m':e.tolist(),
     'command_jacobian_inverse_norm':float(np.linalg.norm(np.linalg.inv(j),2))})
  out={'scope':'offline_split_QP_IK_not_production10ms_or_task_acceptance','fixture':str(fp),
    'fixture_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'job_id':121,
    'qp_iterations':int(result[206]),'qp_original_residual':float(result[204]),
    'clearance_min':float(min(clear)),'bounds_min':float(min(bounds)),
    'rows':rows,'native_optimizer':value._optimizer.provenance,'delta':dict(zip(feet,delta.tolist()))}
 finally:value.close()
target=b/('nonlinear-servo-'+str(uuid.uuid4())+'.json');target.write_text(json.dumps(out,indent=2))
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(target),'qp_iterations':out['qp_iterations'],'rows':sorted(rows,key=lambda r:-r['excess_nm'])[:4]}))
