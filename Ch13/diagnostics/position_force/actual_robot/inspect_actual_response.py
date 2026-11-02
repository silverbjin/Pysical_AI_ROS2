"""Locate equilibrium-versus-contact-kinematic mismatch in completed data."""
import runpy,sys,json,uuid
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
script=Path(__file__).resolve().parent/'analyze_actual_robot_probe.py'
g=runpy.run_path(str(script),init_globals={'_analysis_reuse':True})
data=g['data'];model=g['model'];pose0=g['pose0'];names=g['names'];nq=g['nq'];delta=g['delta']
def position(case):
 body=case['last_body'];r=Rotation.from_quat(body['orientation']).as_matrix()
 return np.r_[np.array(body['position'])-pose0[:3,3],Rotation.from_matrix(r@pose0[:3,:3].T).as_rotvec(),
   [case['mean_joint_positions'][n] for n in names]]
dx=np.column_stack([(position(data['cases'][1+2*i])-position(data['cases'][2+2*i]))/(2*delta) for i in range(12)])
df=g['observed'];eq=g['grad']@dx+model['mapped']@df+g['input_matrix'][:nq,:]
kin=model['contact']@dx
baseline=g['baseline'];measured_centers=np.array([r['center_world'] for r in data['baseline']['contacts']['feet']])
centers_error=np.max(np.abs(model['foot_centers']-measured_centers))
vel_columns=np.column_stack([(np.array([data['cases'][1+2*i]['mean_joint_velocities'][n] for n in names])-
 np.array([data['cases'][2+2*i]['mean_joint_velocities'][n] for n in names]))/(2*delta) for i in range(12)])
with_velocity=eq-np.r_[np.zeros((6,12)),model['damping'][6:,None]*vel_columns]
result={'scope':'completed actual model perturbation residual decomposition, no engine retry',
 'center_FK_max_error_m':float(centers_error),
 'equilibrium_residual_by_input':dict(zip(data['leg_names'],np.max(np.abs(eq),axis=0).tolist())),
 'with_mean_Dv_residual_by_input':dict(zip(data['leg_names'],np.max(np.abs(with_velocity),axis=0).tolist())),
 'contact_velocity_constraint_residual_by_input':dict(zip(data['leg_names'],np.max(np.abs(kin),axis=0).tolist())),
 'baseline_force_std_max_n':max(baseline['force_std_flat']),
 'all_cases_force_std_max_n':max(max(c['force_std_flat']) for c in data['cases']),
 'all_cases_mean_velocity_max_rps':max(max(abs(v) for v in c['mean_joint_velocities'].values()) for c in data['cases']),
 'baseline_last_vs_mean_q_max_rad':max(abs(r['position']-baseline['mean_joint_positions'][r['name']]) for r in data['baseline']['controls']['joints'])}
p=g['out']/('residuals-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(result,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),**result},indent=2))
