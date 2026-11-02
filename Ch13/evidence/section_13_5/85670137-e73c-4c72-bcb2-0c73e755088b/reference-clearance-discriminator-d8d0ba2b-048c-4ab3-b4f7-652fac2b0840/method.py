"""Closed original reference: identify which independent leg path is invalid."""
from pathlib import Path
import hashlib,json,uuid
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.leg_kinematics import ik_leg,thigh_trunk_clearance
from integrated_robot_navigation.carry_profile import default_limits

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g2-gazebo-b82af967-a8a8-4e11-9612-6db8cb5d6695'
closed=json.loads((trial/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((trial/'controller_report.json').read_text());f=report['first_fault']
run=json.loads((trial/'result.json').read_text());model=compile_model(Path(run['scene']['robot']['path']).read_text())
q=f['samples']['joints']['data']['position'];inverse=np.linalg.inv(f['reference_body']);limits=default_limits();rows=[]
for foot,point in f['targets'].items():
    names=[foot[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
    for dz in (-.010,0.,.010,.020):
        target=np.array(point);target[2]+=dz
        values=ik_leg(model,foot,(inverse@np.r_[target,1.])[:3],tuple(q[n] for n in names))
        clear=thigh_trunk_clearance(model,foot,values)
        row=dict(foot=foot,dz=dz,angles=values,clearance_m=clear,
            gait_bounds=all(limits['gait_joint_bounds'][p][0]<=v<=limits['gait_joint_bounds'][p][1]
                for p,v in zip(('hip','thigh','calf'),values)))
        rows.append(row)
out=base/('reference-clearance-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='post_reap_original_reference_geometry_and_independent_vertical_extrema_not_physical_replay',
    trial=trial.name,input_sha256=hashlib.sha256((trial/'controller_report.json').read_bytes()).hexdigest(),
    phase_context=f['phase_context'],selected=f['state_before']['swing_foot'],rows=rows,
    load_balance_plan=f['load_balance_plan'])
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),selected=value['selected'],rows=rows)),flush=True)
