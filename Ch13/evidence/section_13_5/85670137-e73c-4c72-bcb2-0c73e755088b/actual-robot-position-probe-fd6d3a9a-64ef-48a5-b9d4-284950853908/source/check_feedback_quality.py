"""Physical-scale error and local balanced-force feedback, not a rewritten fit PASS."""
import runpy,sys,json,uuid
from pathlib import Path
import numpy as np
g=runpy.run_path(str(Path(__file__).resolve().parent/'analyze_actual_robot_probe.py'),init_globals={'_analysis_reuse':True})
predicted=g['predicted'];observed=g['observed'];delta=g['delta'];model=g['model']
_,singular,vh=np.linalg.svd(model['contact'][:,:6].T,full_matrices=True)
assert singular[-1]>1e-8
null=vh[6:].T
control=np.linalg.pinv(null.T@predicted,rcond=1e-9)
iteration=null-observed@control
rho=float(np.linalg.norm(iteration,2))
cosines=np.sum(predicted*observed,axis=0)/(np.linalg.norm(predicted,axis=0)*np.linalg.norm(observed,axis=0))
absolute=np.linalg.norm((predicted-observed).reshape(4,3,12),axis=1)*delta
result={'scope':'functional_feedback_quality_on_existing_microinput_data_not_new_acceptance',
 'relative_5percent_diagnostic_still_failed':not g['result']['passed'],
 'max_force_vector_error_at_actual_input_n':float(np.max(absolute)),
 'min_force_change_direction_cosine':float(np.min(cosines)),
 'local_balanced_force_error_contraction_2norm':rho,
 'balanced_force_subspace_dimension':null.shape[1],
 'interpretation':'Contraction is local and unconstrained; not a proof of saturated QP, unloading duration, tripod path or C1/G2.',
 'next':'Define book validation in physical force units and held-out larger safe inputs before any new runtime model adoption; preserve original5percentFAIL.'}
p=g['out']/('feedback-quality-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(result,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(p),**result},indent=2))
