"""Read-only, first-order contact compliance discriminator, NOT engine proof."""
import hashlib,json,uuid,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.projection import body_rotation

repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/(sys.argv[1] if len(sys.argv)>1 else 'native-g2-gazebo-1a27f18c-e6c7-4d36-b7f4-99a245f79d0f')
assert trial.parent==base and trial.name.startswith('native-g2-gazebo-')
closed=json.loads((trial/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
result=json.loads((trial/'result.json').read_text());report=json.loads((trial/'controller_report.json').read_text())
fault=report['first_fault'];model=compile_model(Path(result['scene']['robot']['path']).read_text())
assert model.model_sha256==fault['model_sha256']
contacts=fault['samples']['contacts']['data'];forces=np.asarray(contacts['forces'])
points=np.asarray(contacts['points']);q=fault['samples']['joints']['data']['position']
rotation,_=body_rotation(fault['samples']['body']['data'])
tree=ET.fromstring(model.urdf);rows=[];compliance=[]
for foot in model.feet:
    names=[foot[:2]+'_'+part+'_joint' for part in ('hip','thigh','calf')]
    angles=np.asarray([q[n] for n in names]);derivative=[];gains=[]
    for index,name in enumerate(names):
        gain=float(tree.findtext(f"ros2_control/joint[@name='{name}']/param[@name='ch13_kp']"));gains.append(gain)
        delta=np.zeros(3);delta[index]=1e-6
        derivative.append(float(rotation[2]@(np.asarray(fk_leg(model,foot,angles+delta))-fk_leg(model,foot,angles-delta)))/(2e-6))
    c=float(np.sum(np.square(derivative)/gains));compliance.append(c)
    rows.append(dict(foot=foot,world_vertical_jacobian=derivative,kp=gains,compliance_m_per_n=c))
h=np.column_stack((np.ones(4),points[:,1],-points[:,0]));_,_,vh=np.linalg.svd(h.T);null=vh[-1]
selected=model.feet.index(fault['state_before']['swing_foot']);delta_force=-forces[selected]*null/null[selected]
# Excluded foot remains governed by its ORIGINAL <=10mm unload. Only the
# other three command references provide this first-order comparison.
delta_z=-np.asarray(compliance)*delta_force;delta_z[selected]=0
k=np.diag(1/np.asarray(compliance));p=k-k@h@np.linalg.solve(h.T@k@h,h.T@k)
predicted=forces-p@delta_z
weights=np.asarray(compliance)*null*null;coupling=float((weights.sum()-weights[selected])/weights.sum())
normalized=delta_z/coupling;predicted_normalized=forces-p@normalized
out=base/('contact-load-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='linearized_flat_static_flexibility_not_causal_engine_replay',trial=trial.name,
    report_sha256=hashlib.sha256((trial/'controller_report.json').read_bytes()).hexdigest(),
    source_manifest_sha256=hashlib.sha256((trial/'source_manifest.json').read_bytes()).hexdigest(),
    measured_forces_n=list(forces),nullspace=list(null),wrench_residual=list(h.T@null),
    desired_tripod_forces_n=list(forces+delta_force),support_reference_delta_m=list(delta_z),
    linear_predicted_forces_after_support_only_n=list(predicted),rows=rows,
    held_foot_coupling_fraction=coupling,inverse_coupling=1/coupling,
    normalized_support_delta_m=list(normalized),normalized_linear_predicted_forces_n=list(predicted_normalized),
    caveats=['asynchronous measured samples; flat vertical small-deflection model only',
        'omits joint gravity, tangential friction, contact damping, dynamics and changing Jacobian',
        'no runtime command or simulator state was changed; no acceptance granted'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),**value)),flush=True)
