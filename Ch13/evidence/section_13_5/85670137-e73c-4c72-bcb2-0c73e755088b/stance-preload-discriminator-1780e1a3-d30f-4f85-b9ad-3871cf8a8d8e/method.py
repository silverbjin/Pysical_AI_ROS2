"""Post-reap comparison of held references and measured feet; no physics replay."""
import hashlib,json,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model,initial_leg_targets
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.projection import body_rotation

repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g2-gazebo-bd67d364-2f02-4537-abb0-c09558fc95b6'
closed=json.loads((trial/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
result=json.loads((trial/'result.json').read_text())
report_path=trial/'controller_report.json';report=json.loads(report_path.read_text())
fault=report['first_fault'];reference=np.array(fault['reference_body'])
model=compile_model(Path(result['scene']['robot']['path']).read_text())
assert model.model_sha256==fault['model_sha256']
held=initial_leg_targets(model)
measured_q=fault['samples']['joints']['data']['position']
body=fault['samples']['body']['data'];rotation,_=body_rotation(body)
observations=[]
for index,foot in enumerate(model.feet):
    names=[foot[:2]+'_'+part+'_joint' for part in ('hip','thigh','calf')]
    local=np.array(fk_leg(model,foot,tuple(measured_q[n] for n in names)))
    initial_local=np.array(fk_leg(model,foot,tuple(held[n] for n in names)))
    seed=(reference@np.r_[initial_local,1.])[:3]
    observed=rotation@local+body['position']
    in_reference=(reference@np.r_[local,1.])[:3]
    target=fault['targets'][foot]
    observations.append(dict(foot=foot,held_command_z_in_reference=seed[2],
        target_z=target[2],target_minus_held_z_m=target[2]-seed[2],
        initial_measured_floor_z=report['current']['floor'][foot],
        measured_world_center_z=observed[2],measured_joint_FK_in_reference_z=in_reference[2],
        selected_force_n=fault['samples']['contacts']['data']['forces'][index]))
out=base/('stance-preload-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='read_only_reference_vs_measurement_not_causal_physics_proof',
    trial=trial.name,report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
    source_manifest_sha256=hashlib.sha256((trial/'source_manifest.json').read_bytes()).hexdigest(),
    fault=dict(reason=fault['reason'],ros_ns=fault['ros_ns'],wall_ns=fault['wall_ns'],
               state=fault['state_before'],phase_context=fault['phase_context']),
    body_reference_z=reference[2,3],actual_body_z=body['position'][2],rows=observations,
    caveats=['body/joint/contact captures differ; no exact coincident physics inferred',
        'The static held-q FK is expressed in the fault reference pose; inspect preserved z/roll/pitch before interpreting it as activation preload',
        'Reference loss is a hypothesis for remaining load, not a completed physical counterfactual'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),**value)),flush=True)
