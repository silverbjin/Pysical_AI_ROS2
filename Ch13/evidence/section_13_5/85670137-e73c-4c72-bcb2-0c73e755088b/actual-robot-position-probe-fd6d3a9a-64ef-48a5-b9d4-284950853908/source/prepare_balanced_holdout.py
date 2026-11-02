"""Theory-selected held-out balanced input; no measured Jacobian fitting."""
import runpy,sys,json,uuid,copy,hashlib
from pathlib import Path
import numpy as np
g=runpy.run_path(str(Path(__file__).resolve().parent/'analyze_actual_robot_probe.py'),init_globals={'_analysis_reuse':True})
pred=g['predicted'];model=g['model'];leg_names=g['data']['leg_names']
_,s,vh=np.linalg.svd(model['contact'][:,:6].T,full_matrices=True);assert s[-1]>1e-8
null=vh[6:].T
desired=np.zeros(12);desired[2]=-.5
desired=null@(null.T@desired)
control=np.linalg.pinv(null.T@pred,rcond=1e-9)@(null.T@desired)
fixture=copy.deepcopy(g['fixture']);fixture['args']['joints']=dict(g['config']['targets'])
command= g['build'](fixture,sphere_plane_points=True)
fixture['args']['points']=dict(zip(command['feet'],command['foot_centers'].tolist()))
center_model=g['build'](fixture)
cartesian=center_model['contact'][:,center_model['leg_indices']]@control
largest=max(np.sum(np.abs(row)) for row in cartesian.reshape(4,3))
scale=min(1.,.99*40e-6/largest);control*=scale
baseline_centers=center_model['foot_centers'];excursions=[]
perturb={n:float(v) for n,v in zip(leg_names,control)}
for sign in (1.,-1.):
 test=copy.deepcopy(fixture)
 for name,value in perturb.items():test['args']['joints'][name]+=sign*value
 centers=g['build'](test)['foot_centers'];excursions.append(float(np.max(np.sum(np.abs(centers-baseline_centers),axis=1))))
assert max(excursions)<=40e-6
plan={'scope':'predefined_theory_selected_balanced_force_holdout_not_runtime_command_permission',
 'parent_probe':str(g['out']),'perturbations':[{},perturb,{n:-v for n,v in perturb.items()}],
 'input_ramp_steps':100,'expected_force_change_flat_n':(pred@control).tolist(),
 'exact_command_foot_L1_excursions_m':excursions,'per_reference_step_envelope_m':40e-6,
 'physical_criterion':{'max_force_vector_prediction_error_n':.1,'balanced_target_error_ratio_max':.5,
  'all_measured_support_forces_min_n':2.,'normal_server_and_ROS_exit':True},
 'rationale':'0.1N is5% of original2N release threshold; ratio0.5 requires a genuine error decrease, not exact matching of a near-zero derivative.',
 'raw_5percent_micro_derivative_FAIL_remains':True,'model_parameters_fitted':False,
 'selection_uses_observed_derivative':False,
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
p=g['out']/('balanced-holdout-plan-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(plan,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),'exact_excursions_m':excursions,'expected_change_n':plan['expected_force_change_flat_n'],
 'max_joint_delta_rad':float(np.max(np.abs(control))),'criteria':plan['physical_criterion']},indent=2))
