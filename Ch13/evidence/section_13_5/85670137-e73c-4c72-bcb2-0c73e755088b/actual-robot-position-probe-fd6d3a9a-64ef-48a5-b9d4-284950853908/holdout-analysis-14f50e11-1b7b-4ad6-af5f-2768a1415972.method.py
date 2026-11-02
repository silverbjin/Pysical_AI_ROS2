"""Evaluate preregistered physical-scale held-out force task after closure."""
import json,sys,hashlib,uuid
from pathlib import Path
import numpy as np
out=Path(sys.argv[1]);plan=json.loads((out/'holdout_plan.json').read_bytes())
data=json.loads((out/'run.stdout').read_bytes());closure=json.loads((out/'closure.json').read_bytes())
assert data['completed'] and len(data['cases'])==3
pred=np.array(plan['expected_force_change_flat_n'])
observed=(np.array(data['cases'][1]['mean_forces_world_flat'])-
 np.array(data['cases'][2]['mean_forces_world_flat']))/2
error=observed-pred
absolute=float(np.max(np.linalg.norm(error.reshape(4,3),axis=1)))
ratio=float(np.linalg.norm(error)/np.linalg.norm(pred))
min_support=min(min(np.array(c['mean_forces_world_flat']).reshape(4,3)[:,2]) for c in data['cases'])
criterion=plan['physical_criterion']
normal=closure['normal_process_return'] and closure['server_destroyed'] and closure['ROS_shutdown'] and not closure['residual']
passed=bool(normal and absolute<=criterion['max_force_vector_prediction_error_n'] and
 ratio<=criterion['balanced_target_error_ratio_max'] and min_support>=criterion['all_measured_support_forces_min_n'])
result={'scope':'heldout_balanced_force_task_on_actual_URDF_not_G1_C1_G2','passed':passed,
 'predicted_delta_force_flat_n':pred.tolist(),'observed_delta_force_flat_n':observed.tolist(),
 'max_force_vector_prediction_error_n':absolute,'balanced_target_error_ratio':ratio,
 'min_measured_support_force_n':float(min_support),'normal_exit_and_residuals_passed':normal,
 'criterion_fixed_before_run':criterion,'old_micro_derivative5percent_failure_preserved':True,
 'parameters_fitted':False,'selection_used_observed_derivative':False,
 'method_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'input_sha256':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ('holdout_plan.json','run.stdout','closure.json')},
 'limits':'One stationary posture and balanced force perturbation; not saturation, unilateral release, full path, ROS integration or G2 validation.'}
p=out/('holdout-analysis-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(result,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),**result},indent=2));raise SystemExit(0 if passed else 1)
